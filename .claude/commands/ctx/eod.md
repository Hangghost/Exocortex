---
name: ctx:eod
description: 下班總整理。呼叫 state_audit 後依規則自動處理 / 詢問，確保 remote 維持最新、observer 20:00 看得到今日工作。
---

下班（end-of-day）總整理工作流。使用者主動觸發，自動為主、詢問為例外。
與 18:30 cron silent backstop 共享 `infra/periodic_jobs/state_audit/core.py`
的審計邏輯——兩者得到等價的 `AuditReport`，只是 caller policy 不同。

**Input**: `$ARGUMENTS`（保留）。本命令當前不使用 arguments；未來可加 `--no-update` 等 flag。

**關鍵 invariant**：Step 5 之前工作樹必為乾淨。
（Step 3 已處理或 abort，Step 4 squash 舊 content 不引入髒檔，所以 Step 5 不需要 stash，no magic。）

**Step 排序原則（dataflow ordering）**：本 protocol 依資料流分四段：

0. **Worktree 收尾**（Step 0）：對所有活著的 project worktree 跑收尾流程後 hard delete。若機器上無 spawned worktree（`git worktree list` 無 `.claude/worktrees/<name>` 條目），整段 no-op。
1. **Main mutation**（Step 1–4）：fetch → audit → dirty 處理 → 合舊 unmerged content 進 main。這段結束後 main 已前進到當日 `content/<today>` 該 fork 的 SHA。
2. **content/today 工作**（Step 5–7）：建/切 `content/<today>` → bridge-stale project update → 產出 commit。
3. **Push + report**（Step 8–10）：依 D5 表格 push → 結尾報告 → observer-ready hint。

**不可顛倒的關鍵約束**：
- Step 0（worktree 收尾）SHALL 先於 Step 1-10。否則類別 2 提示要使用者搬檔到 main worktree、但 main 上的 EOD 流程已經跑完。
- Step 4（合舊 content）SHALL 先於 Step 5（從 main fork `content/<today>`）。Step 4 是 main 的 producer（squash → main 前進），Step 5 是 main 的 consumer（從 main fork content/today）——protocol 必須讓 producer 先於 consumer。否則跨日 EOD 會讓 `content/<today>` fork 自 stale main，產生孤兒分支。

---

## Step 0 — Project worktree 收尾

Worktree 機制為永遠啟用，無 marker 偵測。直接列出所有活著的 project worktree：

```bash
git worktree list --porcelain | grep -A2 "worktree.*\.claude/worktrees/"
```

若無對應 worktree 條目（例如機器上從未跑過 `/ctx:project resume`），整段 Step 0 為 no-op，直接進入 Step 1。

對每個 `.claude/worktrees/<name>` 路徑跑收尾子流程：

### Step 0.1 — 收尾子流程（每個 worktree）

對單一 worktree path `<wt-path>`：

```bash
cd <wt-path>
git status --porcelain
```

依路徑 prefix 將 dirty 檔案分類：

| 類別 | 路徑 prefix | 處理 |
|------|------------|------|
| 1 | `projects/<X>/` | 自動 commit + push（互動 prompt 確認 message，預設 `project(<X>): <auto-summary>`） |
| 2 | `contexts/`、`inbox/ideas.md`、`inbox/reading_list.md` | 列入「需搬到 main worktree」清單，不自動處理 |
| 3 | `infra/state/`、`memory/`、`inbox/captured/`、`projects/INDEX.md` | 列入警報清單（system-singleton），不自動處理 |
| 4 | `rules/`、`openspec/`、`.claude/` | 列入警報清單（架構變更），不自動處理 |

**處理流程**：

1. 若**類別 1 有變更**：

   ```bash
   cd <wt-path>
   git add projects/<X>/
   # 顯示 prompt 確認 message（預設值由 git diff --stat 衍生）
   git commit -m "<message>"

   # Push：偵測 upstream 是否存在
   if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
     git push
   else
     git push -u origin project/<X>
   fi
   ```

   首次 push 對 newly-created `project/<X>`（如 `/ctx:project resume` 從 main 重建的分支）SHALL 自動加 `-u`，與 Step 8 既有 `no_upstream` auto 規則一致。

2. 若**類別 2/3/4 任一有變更**：顯示對應提示/警報並列出檔案清單：

   ```
   ⚠️ Worktree <name> 內偵測到非預期變更：

   類別 2（應在 main worktree 走 content/<date>）：
     - inbox/ideas.md
     - contexts/blog/<draft>.md

   類別 3（system-singleton，幾乎一定是誤動）：
     - infra/state/system_state.json

   類別 4（架構變更應走 feature/* 分支）：
     - rules/SOUL.md
   ```

   接著用 AskUserQuestion 詢問：

   ```
   是否保留此 worktree 等手動處理？
   1. Yes（預設）— 保留 worktree，下次 /ctx:eod 再處理
   2. No  — 強制 hard delete（dirty 變更會遺失！）

   選擇？
   ```

   - **Yes（預設）**：略過 hard delete，列入結尾報告的「保留」清單，繼續處理下一個 worktree
   - **No**：執行 `git worktree remove --force <wt-path>`，列入「強制刪除」清單

3. 若**只有類別 1 變更（已處理）或無任何變更**：

   ```bash
   cd ~/Documents/Projects/Exocortex-personal  # 切回 main worktree
   git worktree remove <wt-path>
   ```

   列入結尾報告的「自動處理 + hard delete」計數。

### Step 0.2 — 累積結果

把每個 worktree 的處理結果累積到記憶體中的 `worktree_report`，包含：

- `total`：處理的 worktree 數
- `auto_completed`：類別 1 自動 commit + push + delete 的數量
- `clean_deleted`：無變更直接 delete 的數量
- `kept_for_manual`：因類別 2/3/4 警報而保留的清單（含 worktree name + 原因）
- `force_deleted`：使用者選擇強制刪除的清單

此資料供 Step 9 結尾報告引用。

### Step 0.3 — 切回 main worktree

完成所有 worktree 收尾後：

```bash
cd ~/Documents/Projects/Exocortex-personal
```

確保 Step 1 之後在 main worktree 跑（Step 4 squash 等操作必須在 main 工作樹）。

---

## Step 1 — `git fetch --all`

無副作用、永遠執行。確保 local vs upstream 比對基於最新狀態，
解決多機架構（MacBook + Mac mini）下的「另一台機 push 了東西本機還沒看到」race。

```bash
git fetch --all --quiet
```

---

## Step 2 — 跑 audit

```bash
python -m infra.periodic_jobs.state_audit --emit-only
```

或於命令內 import：

```python
from infra.periodic_jobs.state_audit import audit
report = audit()
```

得到 `AuditReport`，含 `findings: list[Finding]`。後續每個 step 都基於這份 report。

> **不重複實作檢查邏輯**——必須使用 `state_audit.core.audit()`，與 cron 共用。

---

## Step 3 — Dirty 處理（詢問）

若 `report.findings` 含 `kind == "dirty_working_tree"` 的 finding：

執行 `git branch --show-current` 取得當前分支名。

**若當前分支前綴為 `feature/`**，用 AskUserQuestion 詢問（feature 專屬文案）：

```
偵測到工作樹有 N 個未提交檔案。

⚠️ 目前在 feature 分支（<branch-name>）。
1. No  — 建議路徑。架構變更應留在 feature 分支內 commit，/ctx:eod 將 ABORT，不執行 step 4 之後任何步驟。
2. Yes — 轉派 /ctx:content（不適合架構工作，架構檔案可能被誤路由到 content/today）。

選擇？
```

**若當前分支前綴不為 `feature/`**，用 AskUserQuestion 詢問（通用文案）：

```
偵測到工作樹有 N 個未提交檔案。
1. Yes — 轉派 /ctx:content（自身會路由 commit + 切到 content/today）
2. No  — ABORT /ctx:eod，不執行 step 4 之後任何步驟

選擇？
```

- **Yes**：呼叫 `/ctx:content`。完成後返回繼續 Step 4。**此時工作樹必為乾淨**。
- **No**：列印「dirty 未處理，project update / push 全部跳過」，結束。

若 audit 未偵測 dirty：跳過此 step，直接進 Step 4。

---

## Step 4 — 未 merged content 分支詢問合併

對 `report.findings` 中 `kind == "unmerged_content_branch"` 的每個 finding：

- 若 `finding.detail.is_today == True`：**靜默略過**（不詢問、不警告）
  - 理由：/ctx:eod 可一日多次執行；當日 content branch 仍在累積中。
  - 「observer 前最後把關」是 18:30 cron 的職責，不是 /ctx:eod 的。
  - 結尾 Step 10 會根據此情境條件式產生 observer-ready hint。
- 若 `finding.detail.is_today == False`：用 AskUserQuestion 逐個詢問

```
偵測到舊 content 分支未合併：content/<earlier-date>
是否合併到 main？
1. Yes — 切到該分支，跑 /ctx:content merge（squash 策略）後切回 content/<today>
2. No  — 跳過，列入「待手動處理」清單
```

> **Lazy-create content/<today>**：合併完舊 content 並讓 main 前進後，需要切回 `content/<today>`。若此分支尚不存在（跨日 EOD 第一次跑、當日尚未建 content branch），SHALL `git checkout -b content/<today> main`——此時 main 已是 squash 後的新 SHA，`content/<today>` 從 fresh main fork。後續 Step 5 偵測到已在 `content/<today>` 自然 no-op。

```bash
today=$(date +%Y-%m-%d)
# ... 對每個 is_today=False 的 finding 跑 /ctx:content merge 後 ...
if git rev-parse --verify content/$today >/dev/null 2>&1; then
  git checkout content/$today
else
  git checkout -b content/$today main
fi
```

若 audit 不含 `unmerged_content_branch`，或所有 finding 皆 `is_today=True`：跳過此 step。

---

## Step 5 — 確保在 `content/<today>` 分支

當前日期（YYYY-MM-DD）為 `<today>`。Step 3 之後工作樹必乾淨，Step 4 squash 不引入髒檔，所以無 stash 風險。

執行：

```bash
current=$(git branch --show-current)
if [ "$current" != "content/$(date +%Y-%m-%d)" ]; then
  if git rev-parse --verify content/$(date +%Y-%m-%d) >/dev/null 2>&1; then
    git checkout content/$(date +%Y-%m-%d)
  else
    git checkout -b content/$(date +%Y-%m-%d) main
  fi
fi
```

> **特殊情境**：使用者起始分支是 `feature/<X>` 且明確不想離開（架構工作中）。
> 此時 Step 3 必偵測 dirty（架構工作通常有未 commit 變更）；使用者選 No → /ctx:eod abort。
> 即「不想離開 feature 分支」自然透過 dirty + No 路徑完整 escape。

> **與 Step 4 lazy-create 的關係**：若 Step 4 已 lazy-create `content/<today>`（合舊 content 路徑），Step 5 偵測到當前分支已是 `content/<today>`，整段 no-op。Step 5 在路徑上仍是 ensure 的權威，與 Step 4 lazy-create 二者語意一致：**從 fresh main fork**。

---

## Step 6 — Bridge-stale active project 自動 update（無詢問）

對 `report.findings` 中 `kind == "stale_active_project_bridge"` 的每個 finding：

```bash
/ctx:project update <finding.detail.project_name>
```

依序、不詢問。每個 update 完會在 `contexts/work_logs/` 產出 `*<name>_update.md`。

> **環境變數 escape**：未來若加上 `CTX_EOD_AUTO_UPDATE=0`，可全 skip 此 step。
> （當前 change scope 不含此 flag；先觀察實際使用情況。）

---

## Step 7 — Step 6 產出後自動 `/ctx:content`

若 step 6 產出新 `_update.md` 檔案（`git status --porcelain` 非空）：

```bash
/ctx:content
```

讓 `/ctx:content` 處理 commit（routing 已在它自身內部完成）。
完成後工作樹再次乾淨，分支仍為 `content/<today>`。

若 step 6 沒跑（無 bridge-stale）或沒產出新檔（罕見）：跳過此 step。

---

## Step 8 — Push 規則（D5 表格）

對所有 push 相關 findings，依下表處理：

| Finding kind | 條件 | 處理 |
|---|---|---|
| `unpushed_branch` | `well_formed_prefix=True` 且 fast-forward | **auto** `git push origin <branch>` |
| `no_upstream` | `well_formed_prefix=True` | **auto** `git push -u origin <branch>` |
| `no_upstream` | `well_formed_prefix=False` | **ask** 是否 push |
| `diverged_from_upstream` | 任何分支 | **ask** rebase / skip / 其他（**永不自動 force-push**） |
| `untracked_remote_branch` | `relation=equal` 且 `well_formed_prefix=True` | **auto** `git branch --set-upstream-to=origin/<branch> <branch>` |
| `untracked_remote_branch` | `relation=ahead` 且 `well_formed_prefix=True` | **auto** `git push -u origin <branch>` |
| `untracked_remote_branch` | `relation=behind` 且 `well_formed_prefix=True` | **auto** `git branch -f <branch> origin/<branch>`（**不 checkout**，同時補 tracking + fast-forward） |
| `untracked_remote_branch` | `relation=diverged` | **ask** rebase / reset / skip |
| `untracked_remote_branch` | `well_formed_prefix=False` | **ask** 是否處理 |
| `branch_behind_origin` | `is_current=False`（含 main 與 project/* 等） | **auto** `git branch -f <branch> origin/<branch>`（**不 checkout**） |
| `branch_behind_origin` | `is_current=True`（極罕見：content/<today> 自己 behind） | **ask** pull / reset / skip（不能用 `git branch -f` 對 current branch） |

`well_formed_prefix` 指分支名為 `content/* | project/* | feature/* | main`。

**Step 5 invariant 保護**：以上所有 auto 規則都不執行 `git checkout`，確保整個 step 8 過程中 current branch 一直是 `content/<today>`。`git branch -f`、`git branch --set-upstream-to`、`git push` 對 non-current branch 都安全；只有 `branch_behind_origin[is_current=True]` 因不能用 `branch -f` 才走 ask 路徑。

> **永不 force-push**。即使使用者選擇處理 diverged，也透過 rebase 後正常 push，
> 不直接 `--force`。若 rebase 失敗或衝突，列入「待手動處理」並結束 step 8。

> **舊 `main_behind_origin` 規則已移除**。先前 `git pull --ff-only origin main` 在 step 5 之後（必在 content/<today>）會錯誤地 merge origin/main commits 到 content/<today>，違反分支隔離 invariant。改由通用 `branch_behind_origin` + `git branch -f main origin/main`（不 checkout）替代。

---

## Step 9 — 結尾報告

輸出格式：

```
## EOD 總整理 — <date>

🌳 Worktree 收尾：
  - 處理 <total> 個 project worktree
  - <auto_completed> 個自動 commit + push + hard delete
  - <clean_deleted> 個乾淨 hard delete
  - <kept_for_manual> 個保留待手動處理：
    · wwpf-qd（類別 3：system_state.json 變更）
    · yoga-cs-agent（類別 2：inbox/ideas.md 應走 content/<date>）

✅ 自動處理：
  - bridge-stale: <N> 個專案已 /ctx:project update
  - push: <N> 個分支已 push
  - main 已 fast-forward pull

⚠️ 待手動處理（<N> 項）：
  - content/2026-04-30 未合併（使用者選擇 No）
  - feature/foo diverged（使用者選擇 skip）

狀態：✅ remote 全部最新  /  ⚠️ 還有 <N> 項待處理
```

`🌳 Worktree 收尾` 段落 SHALL 在 Step 0 處理過至少一個 worktree 時顯示；若 Step 0 完全 no-op（無 spawned worktree），SHALL NOT 包含此段。

若無任何待處理項（含 worktree 保留清單為空）：以 `✅ remote 全部最新` 作結。

---

## Step 10 — Observer-ready 提示

若 `report.findings` 仍含 `kind == "unmerged_content_branch"` 且 `detail.is_today == True`，
於 step 9 結尾報告下方追加：

```
💡 今日 content 分支尚未合併到 main。
若已準備好讓 20:00 observer 看到今日工作（收尾、不再追加 commit），
請執行 `/ctx:content merge` 將 content/<today> squash 進 main。

/ctx:eod 故意不自動合併 today（一日多次執行、當日內容仍在累積）；
merge 是顯式的「我今天結束了」訊號。
```

若 today 已合併（無此 finding）或當前不在 `content/<today>`：跳過此 step。

---

## Guardrails

- **永不 force-push**（即使使用者明示要求；force-push 由使用者手動執行 `git push --force-with-lease`）
- **永不自動 commit** content 以外的內容；所有 commit 由 `/ctx:content` 路由
- **永不切到非 content/<today> 分支**（除了 step 4 詢問合併舊 content 時暫時切過去）
- **未知前綴永遠詢問**——分支名不在 `content/* | project/* | feature/* | main` 的，
  即使 `unpushed_branch` 也走 ask 路徑
- **/ctx:eod 不接受 `--force` 之類的 flag**——所有「override」必須回到對應的子命令
- 若 step 1 fetch 失敗（network 不通）：列印警告但繼續執行；
  push-related findings 將反映上次 fetch 的快照狀態（與 cron 行為一致）
