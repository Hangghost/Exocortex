---
name: ctx:onboard
description: 開機總整理。fetch → 跑 state_audit → 詢問 dirty 委派 /ctx:content → 讀昨夜 observer/audit findings → 全專案 snapshot → 一頁式 digest 與路由建議。對稱於 /ctx:eod。
---

開機（start-of-day）總整理工作流。使用者主動觸發，read 為主、mutation 由委派處理。
與 `/ctx:eod` 對稱共享 `infra/periodic_jobs/state_audit/core.py` 的審計邏輯——
兩者得到等價的 `AuditReport`，只是 caller policy 不同：
eod 偏 mutation + push（讓 20:00 observer 看到今日工作），
onboard 偏 read-only digest（讓使用者快速回到工作狀態）。

**Input**: `$ARGUMENTS`（保留）。本命令當前不使用 arguments；未來可加 `--no-projects` 等 flag。

**關鍵 invariant**：本命令 SHALL NOT 自動 commit / push / 切分支 / 呼叫 LLM。
所有 mutation 由 Step 3 詢問後委派 `/ctx:content` 處理（feature 分支例外，會 abort）。

**Step 排序原則（dataflow ordering）**：本 protocol 依資料流分兩段：

1. **Mutation 段**（Step 1–3）：fetch → audit → dirty 委派處理。
   結束後工作樹必為乾淨（feature 分支 abort 路徑除外）。
2. **Read 段**（Step 4–7）：讀 audit findings → 讀 observer 條目 → 讀 projects → 輸出 digest。
   純讀檔，不修改任何狀態。

---

## Step 1 — `git fetch --all`

無副作用、永遠執行。確保 local vs upstream 比對基於最新狀態，
解決多機架構（MacBook + Mac mini）下的「另一台機 push 了東西本機還沒看到」race。

```bash
git fetch --all --quiet
```

若 fetch 失敗（網路不通）：列印警告但繼續執行；
audit 結果將反映上次 fetch 的快照狀態（與 cron 行為一致）。
最終 digest 在徽章區標註「⚠️ fetch 失敗，audit 結果可能反映過時 remote」。

---

## Step 2 — 跑 audit

於命令內 import 並呼叫：

```python
from infra.periodic_jobs.state_audit import audit
report = audit()
```

或於 shell 一行 inline：

```bash
python3 -c "from infra.periodic_jobs.state_audit import audit; r=audit(); [print(f.kind, f.detail) for f in r.findings]"
```

得到 `AuditReport`，含 `findings: list[Finding]`。後續每個 step 都基於這份 report。

> **不要用 `python -m infra.periodic_jobs.state_audit`**——package 沒有 `__main__`，會報 `'... is a package and cannot be directly executed'`。
>
> **不重複實作檢查邏輯**——必須使用 `state_audit.core.audit()`，與 `/ctx:eod` 和 18:30 cron 共用。

---

## Step 3 — Dirty 處理（詢問或 abort）

若 `report.findings` 含 `kind == "dirty_working_tree"` 的 finding：

執行 `git branch --show-current` 取得當前分支名。

**若當前分支前綴為 `feature/`**，**ABORT digest**（不執行 step 4 之後）並顯示：

```
⚠️ 偵測到工作樹有 N 個未提交檔案，當前在 feature 分支（<branch-name>）。

架構工作未收尾不該繼續 onboarding digest——dirty 可能是架構工作的中間產物，
委派 /ctx:content 會把架構檔案誤路由到 content/today 分支。

建議先收尾架構工作：
  1. 在 feature 分支內 commit 架構變更（git add + git commit）
  2. /opsx:archive <change-name>
  3. /ctx:merge

完成後重跑 /ctx:onboard。
```

**若當前分支前綴不為 `feature/`**（main / content/* / project/*），用 AskUserQuestion 詢問：

```
偵測到工作樹有 N 個未提交檔案。
（多為 overnight cron 寫入：memory/OBSERVATIONS.md、infra/state/system_state.json、
 inbox/captured/<yesterday>_state_audit.md）

1. Yes — 委派 /ctx:content 處理（自動依分支類型路由 commit）
2. No  — 繼續 digest，dirty 保持未動，於最終徽章區標註「⚠️ dirty N 個未處理」

選擇？
```

- **Yes**：呼叫 `/ctx:content`。完成後返回繼續 Step 4。**此時工作樹必為乾淨**。
- **No**：繼續 Step 4；於 Step 7 digest 徽章區註明「⚠️ dirty <N> 個未處理」。

若 audit 未偵測 dirty：跳過此 step，直接進 Step 4。

---

## Step 4 — 讀昨晚 state_audit findings

當前日期為 `<today>`（YYYY-MM-DD），昨日為 `<yesterday>`。

讀取 `inbox/captured/<yesterday>_state_audit.md`：

- 檔案存在 → 讀全文，於 Step 7 digest 中以「📋 昨日 audit findings」段落顯示摘要
- 檔案不存在 → 靜默跳過（昨日 audit 未產生 findings 或 cron 未跑）

> **資料來源**：`infra/periodic_jobs/state_audit/cron.py` 在 18:30 跑時，
> 若 `findings` 非空才寫此檔。檔案存在 ≡ 昨日有實際 finding 待人工確認。

---

## Step 5 — 昨夜 observer 條目分流呈現

讀取 `memory/OBSERVATIONS.md` 中最近 3 個 `Date:` block。
**注意**：是「最近 N 個 date block」（reverse-walk 從檔尾），不是「日期範圍」——
observer 不一定每天跑，pure date 計算可能撈到空集合。

### 取最近 3 個 date block（reference 實作）

```python
import re
text = open('memory/OBSERVATIONS.md').read()
parts = re.split(r'^(Date: \d{4}-\d{2}-\d{2})$', text, flags=re.MULTILINE)
# parts = [preamble, "Date: ...", body, "Date: ...", body, ...]
blocks = [parts[i] + parts[i+1] for i in range(1, len(parts), 2)]
last3 = blocks[-3:]
```

> **不要用 `awk '/^Date: '$today'/,EOF'`**——這會 match 從某 date 到檔尾，
> 不是「最近 N 個 block」；且 today 不存在於檔內時整段空集合。
> 也**不要用 `tac`**——macOS BSD 沒有，需用 `tail -r` 或 Python re.split。

### 5.1 — Reflector last run 檢查

讀 `infra/state/system_state.json` 的 `roles.reflector.last_finished_at`：

- 距今 ≤ 10 天 → 正常
- 距今 > 10 天 → 於 step 7 digest 的 axiom watch 區頂部顯示「⚠️ reflector 已 X 天未跑，請檢查 cron」

### 5.2 — 🔴 Axiom watch（被動高亮）

從最近 3 個 date block 中 grep `🔴` 開頭的行：

```python
for b in last3:
    for line in b.splitlines():
        if line.startswith("🔴"):
            yield line
```

- 列出原文（不蒸餾、不 LLM 摘要）
- 條目最多顯示 3 條（更多時顯示「...及 N 條，跑 reflector 看完整蒸餾」）
- **不主動建議 propose axiom**——reflector weekly 蒸餾才是 axiom 晉升正規路徑
- 軟註解：「reflector weekly 自動蒸餾；若覺得已是 trend，可手動 /opsx:propose <axiom-name>」

### 5.3 — 🟡 Skill candidate hints（agent 語意判斷）

從最近 3 個 date block 抽出**所有 🟡 條目原文**，由 agent 對每條判斷：

> 「這條觀察是否描述一個**重複出現、可被封裝成 SOP / skill** 的工作流程？」

**判斷準則**：

- **YES** — 含「我又做了一遍 X」「重複手動 Y」「應該自動化 Z」這類 pattern 描述；或描述了明確的 step-by-step 流程；或標記 `[工作流/*]`、`[流程/*]`、`[方法論/*]` tag
- **NO** — 純粹是專案進度、技術決策、單次 incident、錯誤紀錄、stale 警示
- **邊緣** — 兩者皆有 → 偏保守傾向不列入；若列入需加 `?` 標記

> **為何切 agent 語意判斷而非 grep**：observer.py prompt 不強制標準 tag，實際資料 tag 散亂；
> 純 grep 召回率低、誤報多。Agent 已在 session 內讀條目 render digest，**判斷是零增量成本**。
> Skill 識別本質是語意問題，不是字串問題。
>
> **與 reflector 的角色分工**：reflector weekly 才是 axiom/skill **入庫的 guardian**（寫 rules/）；
> onboard 只 hint 不寫，無 noise 污染風險，因此可以更積極判斷。

**輸出格式**：

```
🟡 <條目原文> → 考慮 /opsx:propose skill <agent 推測的 kebab-case 命名>
```

- 命名由 agent 從條目語意推導
- 最多顯示 5 條
- 軟措辭用「考慮」而非「應該」，避免過度提示壓力
- Agent SHALL 偏保守判斷，寧可漏報也不過度提示

### 5.4 — 無候選的退路

若 5.2 與 5.3 皆無條目命中：digest 中標註「✅ 無 axiom / skill 候選條目」並繼續 Step 6。

---

## Step 6 — 全專案 snapshot

### 6.1 — 取 active 專案列表

讀取 `projects/INDEX.md` 的表格部分，篩出 `status` 欄位為 `active` 的列。

### 6.2 — 對每個 active 專案抓「下一步」

對每個 active 專案 `<name>`：

1. 讀 `projects/<name>/PROJECT.md`
2. 找 `## 下一步` heading 後的第一段非空文字（最多取 80 字）作為 `next_step`
3. 若無 `## 下一步` heading → 退回讀 frontmatter 的 `description` 欄位
4. 若 frontmatter 也無 → `next_step = "⚠️ PROJECT.md 缺下一步段落"`

### 6.3 — Staleness 旗標

對每個專案計算 `last_updated`（從 INDEX.md 取）距今天數：

- ≤ 14 天 → 無旗標
- \> 14 天 → 標 ⚠️ stale

### 6.4 — 無 active 專案的退路

若 INDEX.md 中無 `status: active` 條目：顯示「目前無 active 專案」並繼續 Step 6.5。

---

## Step 6.5 — Inbox reconciliation（事實對照）

對 `inbox/todos.md` Active 區段與 `inbox/ideas.md` 全部內容，由 agent 在 session 內做語意對照，輸出 0–N 條建議於 Step 7 digest 的「📌 Inbox reconciliation」區塊。

**目的**：補 observer staleness（時間維度）的盲點——條目內容跟現況**事實一致性維度**的 drift。三類常見 drift：todo 已做完但忘了 mark `[x]`、todo 描述跟現況不符、idea 已演化成 archived change 但仍躺在 inbox。

### 6.5.1 — 證據來源

agent 對照下列已在 session 內可取的證據（不額外 spawn subagent、不打 LLM API；屬 session 內 reasoning，與 Step 5.3 skill candidate hint 同模式）：

1. `inbox/todos.md` Active 區段（待對照目標）
2. `inbox/ideas.md` 全部（待對照目標）
3. Step 2 的 audit findings（即時系統事實）
4. Step 6 的 project snapshot（含 last_updated）
5. 最近 30 天 `git log --oneline`（commit / merge 證據）
6. 最近 30 天 `openspec/changes/archive/` 目錄列表（archived change 名稱）

### 6.5.2 — 4 類分流（todos vs ideas 動作不同）

| 類別 | 來源 | 觸發條件（保守判定） | 建議動作（弱措辭） |
|---|---|---|---|
| ✅ 看似已完成 | todos.md | 條目敘述對應的工作有明確完成證據（archive / commit / audit ok 連續多日） | → 建議 mark `[x]` |
| 🔄 事實已變 | todos.md | 條目描述跟現況不符（依賴改、架構改、依據已不存在） | → 建議重寫或刪除 |
| 🟢 前置就緒 | todos.md | 條目明示前置條件，且該前置已從現況證據看到滿足 | → 提示「前置已就緒，可開始」 |
| 📦 已演化 | ideas.md | idea 標題 / 描述跟某 archived change 高度重疊 | → 建議移除或註明已歸檔為 `<change-name>` |

`inbox/reading_list.md` SHALL NOT 納入對照——消化路徑為「看完寫心得」（→ `contexts/survey_sessions/` 或 KnowledgeWiki），非 mark done，性質不同。

### 6.5.3 — 顯示上限與摺疊

每類最多 3 條，4 類合計上限 8 條。超過上限時尾端附「…及 N 條，跑 /opsx:propose 處理」摺疊提示，避免 digest 超出 60 行預算。

### 6.5.4 — 措辭、裁決、保守偏向

- 所有建議 SHALL 使用弱措辭（「→ 建議 X」「→ 看似 Y」），不使用「必須」「應該」等強制語氣
- user 最終裁決；命令 SHALL NOT 詢問是否套用建議
- 命令 SHALL NOT 自動編輯 `inbox/todos.md` 或 `inbox/ideas.md`（讀取來源；mutation 由 user 自行 edit、或於對話中告訴 agent 後走 `/ctx:content`）
- 判定邊緣（證據不充分）時 SHALL 不顯示該條目——**漏報 > 誤報**

### 6.5.5 — 零提示退路

若 4 類皆無命中：Step 7 digest 整段省略「📌 Inbox reconciliation」區塊（不顯示「✅ 無建議」這類空白宣告，與 step 5.4 / 6.4 退路 pattern 對齊）。

---

## Step 7 — 一頁式 digest 與路由建議

### 7.0 — Worktree 狀態偵測

列出活著的 project worktree（無 marker 檢查；worktree 機制為永遠啟用）：

```bash
git worktree list --porcelain | grep -A1 "\.claude/worktrees/" | grep "^worktree" | sed 's|.*/||'
```

- 若無條目：跳過 7.0，digest 不顯示 worktree 相關行
- 若有條目：取得名稱清單（例：`wwpf-qd`、`yoga-cs-agent`）
  - 對每個 worktree 名稱對應的 `projects/<name>/PROJECT.md` 檢查 `last_updated`：
    - 距今 ≤ 1 天 → 正常 active worktree
    - 距今 > 1 天 → 列為 stale worktree（隱含前次 EOD 未走完收尾或被使用者保留）

  記錄結果供 7.1 徽章區與 7.2 路由建議使用。

### 7.1 — 輸出格式

依以下固定順序輸出單一訊息（建議 < 60 行）：

```
## 開機 digest — <today>

📡 系統狀態
  ✅ remote 同步 / ⚠️ fetch 失敗
  📦 dirty: <N> files（已委派 /ctx:content / 已標未處理 / 無）
  ⚠️ 待處理 audit findings: <N>
  🔥 role failures: <role>（last failed YYYY-MM-DD）, <role>（last failed YYYY-MM-DD）
  🌳 active worktrees: <N> (<name1>, <name2>)
  ⚠️ 未收尾的 worktree: <N>（<name>: last_updated <date>）

📋 昨日 audit findings（若 step 4 讀到）
  · <finding 1 摘要>
  · <finding 2 摘要>

🔴 Axiom watch（reflector weekly 蒸餾中；last run: X 天前）
  · <條目原文 1>
  · <條目原文 2>

🟡 Skill candidate hints（SOP 化機會）
  · <條目原文 1> → 考慮 /opsx:propose skill <name>
  · <條目原文 2> → 考慮 /opsx:propose skill <name>

🚀 全專案 snapshot
  | name | last_updated | next-step | flag |
  |---|---|---|---|
  | exocortex-dev | 2026-05-01 | <next-step 摘要> | |
  | yoga-cs-agent | 2026-04-21 | <next-step 摘要> | ⚠️ stale |

📌 Inbox reconciliation（todos / ideas 對照建議；零命中時整段省略）
  [todos] ✅ 看似已完成
    · <條目摘要> → 建議 mark [x]（證據：<commit / archive / audit ok 連續>）
  [todos] 🔄 事實已變
    · <條目摘要> → 建議重寫或刪除（證據：<變化引用>）
  [todos] 🟢 前置就緒
    · <條目摘要> → 前置已就緒，可開始（證據：<前置滿足引用>）
  [ideas] 📦 已演化
    · <idea 標題> → 建議移除或註明已歸檔為 <change-name>
  …及 N 條，跑 /opsx:propose 處理

➡️ 建議下一步
  1. 挑專案推進 → /ctx:project resume <name>（自動 spawn worktree）
  2. SOP 化某流程 → /opsx:propose skill <name>
  3. 收 dirty（若未處理）→ /ctx:content
```

`🌳 active worktrees` 與 `⚠️ 未收尾的 worktree` 兩行 SHALL 僅在 7.0 偵測到至少一個 worktree 時顯示；無 worktree 時 SHALL NOT 包含這兩行。

各區段缺資料時整段省略，digest 不顯示「無 finding / 無候選」這類空白宣告（只在 step 5/6 內部退路顯示）。

### 7.2 — `🔥 role failures` 徽章規則

當 `audit().findings` 含至少一個 `kind == "role_failed_run"`：

- 在「📡 系統狀態」徽章區新增一行 `🔥 role failures: <role>（last failed YYYY-MM-DD）`
- 多個失敗 role 以逗號分隔（例：`🔥 role failures: heptabase_ingest（last failed 2026-05-06）, observer（last failed 2026-05-05）`）
- `last failed YYYY-MM-DD` 取自 finding 的 `detail.last_finished_at`，截到 date 部分；若 `last_finished_at` 為 None 則顯示「last failed unknown」
- 無 `role_failed_run` finding → SHALL NOT 顯示此行（保持徽章區乾淨）

**雙重曝光防護**：`role_failed_run` findings 已在徽章區呈現後，SHALL NOT 重複列在「📋 昨日 audit findings」段落。其他 finding kind 的呈現規則不變。

**被動資訊性質**：徽章區的 `🔥 role failures` 只是讓 user 看到事實，**不主動建議補跑指令** — 保持 onboard 對 mutation 的零參與。user 看到後若想補跑，依 finding 的 `suggested_action`（在「📋 昨日 audit findings」段落或 `inbox/captured/<date>_state_audit.md` 內可查到）自行操作。

---

## Guardrails

- **永不自動 commit**——所有 commit 透過 step 3 委派 `/ctx:content` 才會發生
- **永不自動 push**——早晨剛開機，無新工作累積，等 `/ctx:eod` 統一推
- **永不自動切分支**——step 3 委派 `/ctx:content` 由其自身的路由矩陣處理切換；onboard 本體不執行 `git checkout`（除了 fetch）
- **永不呼叫額外 API**——SHALL NOT spawn subagent、SHALL NOT 打 Anthropic / 其他外部 API；agent 在 session 內讀檔做語意判斷（如 Step 5.3 skill candidate、Step 6.5 inbox reconciliation）OK，因為已在現有 session context
- **永不修改 source 檔案**——`memory/OBSERVATIONS.md`、`rules/`、`projects/<name>/PROJECT.md`、`inbox/todos.md`、`inbox/ideas.md` 為讀取來源，不寫入
- **存在性檢查**——所有讀檔操作 SHALL 對檔案做存在性檢查；不存在時優雅降級（顯示警告或省略段落）而非報錯中止
- **feature 分支 ABORT 路徑無副作用**——除了 step 1 fetch，SHALL NOT 執行任何 git 操作
- **`/ctx:onboard` 不接受 `--force` 之類的 flag**——所有「override」必須回到對應的子命令
- 若 step 1 fetch 失敗（network 不通）：列印警告但繼續執行；
  push-related findings 將反映上次 fetch 的快照狀態（與 cron 行為一致）
