# ctx-eod-command Specification

## Purpose

定義 `/ctx:eod`（end-of-day）下班總整理命令——使用者主動觸發的互動式工作流，呼叫 `state_audit.core.audit()` 後依規則自動處理或詢問使用者。確保下班前工作樹乾淨、bridge-stale 專案被 update、相關分支已 push，讓 20:00 observer 看得到當日工作。與 18:30 cron silent backstop 共享 `state_audit.core.audit()`，差別在 caller policy：cron 永遠寫檔不互動，`/ctx:eod` 互動修復、永不 force-push、永不自動 commit content 以外的內容。
## Requirements
### Requirement: /ctx:eod 提供下班總整理入口

系統 SHALL 提供 `.claude/commands/ctx/eod.md` 作為使用者主動觸發的下班總整理入口，呼叫 `state_audit.core.audit()` 後依規則自動處理或詢問使用者。

#### Scenario: 命令存在於命令清單

- **WHEN** 使用者執行 `/ctx:eod`
- **THEN** 命令被識別並執行；`/help` 或 commands 列表包含此命令

### Requirement: 嚴格執行順序

`/ctx:eod` SHALL 依以下順序執行，順序的關鍵 invariant 是「step 5 之前工作樹必為乾淨」與「`content/<today>` 必須從 fresh main fork（即所有舊 unmerged content 已 squash 進 main 後才建）」：

0. 列舉所有活著的 project worktree（透過 `git worktree list`，過濾 `.claude/worktrees/<name>` 路徑），對每個 worktree 跑 worktree 收尾流程（依「Worktree 收尾流程」requirement），完成後 hard delete 該 worktree。若無對應 worktree 條目，整段 no-op
1. `git fetch --all`
2. `core.audit()` → 得 AuditReport
3. 若 findings 含 `dirty_working_tree`：詢問使用者是否轉派 `/ctx:content`
4. 對每個 `unmerged_content_branch` 且 `is_today=False` 的 finding，逐個詢問是否合併（squash 進 main）；合併過程若需切回 `content/<today>` 而後者尚不存在，SHALL lazy-create from fresh main
5. 確保在 `content/<today>` 分支（若不在則 checkout，必要時 `-b content/<today> main`）
6. 對每個 `stale_active_project_bridge` finding，自動跑 `/ctx:project update <name>`
7. 若 step 6 產出新檔，自動跑 `/ctx:content` 提交
8. 對每個 push 相關 finding 採用 D5 規則處理（auto / ask）
9. 輸出結尾報告
10. Observer-ready hint（條件式顯示，見「Observer-ready hint」requirement）

**dataflow ordering 原則**：
- step 0（worktree 收尾）必須先於 step 1-10，否則類別 2 提示要使用者搬檔到 main worktree、但 main 上的 EOD 流程已經跑完
- step 4（合舊 content 進 main）必須先於 step 5（從 main fork content/today），否則跨日 EOD 會讓 content/today fork 自 stale main，產生孤兒分支

Worktree 機制為永遠啟用——無 marker 偵測，所有機器一致行為（path 為 repo-relative 的 `.claude/worktrees/<name>/`）。

#### Scenario: 髒檔被使用者選擇處理

- **WHEN** audit 偵測 dirty_working_tree，使用者回應「Yes 跑 /ctx:content」
- **THEN** /ctx:eod 轉派 /ctx:content；後者完成後返回 /ctx:eod step 4，工作樹此時必乾淨

#### Scenario: 髒檔被使用者選擇不處理

- **WHEN** audit 偵測 dirty_working_tree，使用者回應「No」
- **THEN** /ctx:eod 中止，不執行 step 4 之後任何步驟，並回報「dirty 未處理，project update / push 跳過」

#### Scenario: 工作樹乾淨時直接進 step 4

- **WHEN** audit 不含 dirty_working_tree finding
- **THEN** /ctx:eod 跳過 step 3 詢問，直接進 step 4 處理舊 unmerged content

#### Scenario: 跨日 EOD 從 fresh main fork content/today

- **WHEN** /ctx:eod 在 2026-05-05 執行，本地存在 content/2026-05-04（未合併到 main，含 7 commit）
- **THEN** step 4 先 squash content/2026-05-04 → main（main 前進到含 daily snapshot 的新 SHA），step 5 才從新的 main 建 content/2026-05-05；content/2026-05-05 不會 fork 自 squash 前的舊 main

#### Scenario: 合舊 content 後切回 lazy-create content/today

- **WHEN** step 4 squash content/2026-05-04 後需要切回 content/<today>，但 content/2026-05-05 尚未存在
- **THEN** /ctx:eod SHALL lazy-create `content/2026-05-05` from main（剛 squash 後的新 SHA），並切換過去；step 5 偵測到已在 content/<today> 即 no-op

#### Scenario: 無活著的 project worktree

- **WHEN** `/ctx:eod` 在 `git worktree list` 中無任何 `.claude/worktrees/<name>` 條目的環境執行
- **THEN** 系統 SHALL step 0 為 no-op，繼續從 step 1 執行

### Requirement: 自動處理項

以下 finding SHALL 由 /ctx:eod 自動處理，不詢問使用者：

- `stale_active_project_bridge` → 跑 `/ctx:project update <name>`
- `unpushed_branch` 且 `well_formed_prefix` 且 fast-forward → `git push`
- `no_upstream` 且 `well_formed_prefix` → `git push -u origin <branch>`
- `untracked_remote_branch` 且 `well_formed_prefix`，依 `detail.relation` 分流：
  - `equal` → `git branch --set-upstream-to=origin/<branch> <branch>`（補 tracking 即可）
  - `ahead` → `git push -u origin <branch>`（沿用 no_upstream 行為）
  - `behind` → 套用下方 `branch_behind_origin` auto 規則（無 tracking + behind 等於 fast-forward 本地，補 tracking 由 `branch -f` 同步達成）
  - `diverged` → ask（見下方詢問處理項）
- `branch_behind_origin` 且 `well_formed_prefix` 且 `detail.is_current=False` → `git branch -f <branch> origin/<branch>`（不 checkout，對任意 well-formed 分支包含 main 一致適用）

`well_formed_prefix` SHALL 指 `content/* | project/* | feature/* | main`。

#### Scenario: Bridge-stale 自動 update

- **WHEN** audit 偵測兩個 bridge-stale 專案 A 與 B
- **THEN** /ctx:eod 依序跑 `/ctx:project update A` 與 `/ctx:project update B`，不詢問

#### Scenario: Fast-forward push 自動執行

- **WHEN** audit 偵測本地 `content/2026-05-01` 領先 `origin/content/2026-05-01` 兩個 commit 且可 fast-forward
- **THEN** /ctx:eod 執行 `git push`，不詢問

#### Scenario: 從未 push 的 feature 分支自動 push -u

- **WHEN** audit 偵測本地 `feature/foo` 無 upstream 且無對應 remote ref（從未 push）
- **THEN** /ctx:eod 執行 `git push -u origin feature/foo`，不詢問

#### Scenario: untracked_remote_branch[equal] 自動補 tracking

- **WHEN** audit 偵測 `project/foo` 為 `untracked_remote_branch` 且 `relation=equal`
- **THEN** /ctx:eod 執行 `git branch --set-upstream-to=origin/project/foo project/foo`，不詢問

#### Scenario: untracked_remote_branch[ahead] 自動 push -u

- **WHEN** audit 偵測 `feature/bar` 為 `untracked_remote_branch` 且 `relation=ahead`
- **THEN** /ctx:eod 執行 `git push -u origin feature/bar`，不詢問

#### Scenario: untracked_remote_branch[behind] 套用 branch_behind_origin 規則

- **WHEN** audit 偵測 `project/qheart-ap` 為 `untracked_remote_branch` 且 `relation=behind`，current branch 為 `content/2026-05-01`
- **THEN** /ctx:eod 執行 `git branch -f project/qheart-ap origin/project/qheart-ap`，不詢問（此操作同時補上 tracking 並 fast-forward 本地）

#### Scenario: 非 current 分支落後 origin 自動 fast-forward

- **WHEN** audit 偵測 `branch_behind_origin`，`detail.branch=main`，`detail.is_current=False`
- **THEN** /ctx:eod 執行 `git branch -f main origin/main`，不詢問，不 checkout

#### Scenario: 多個非 current 分支落後同時被處理

- **WHEN** audit 偵測 main 與 `project/qheart-ap` 都 `branch_behind_origin` 且皆非 current
- **THEN** /ctx:eod 對兩者各執行一次 `git branch -f <branch> origin/<branch>`，不詢問

### Requirement: 詢問處理項

以下 finding SHALL 由 /ctx:eod 詢問使用者：

- `dirty_working_tree`（決定是否轉派 /ctx:content）
- `unmerged_content_branch` 且 `is_today=False`（每個逐個詢問是否合併）
- `diverged_from_upstream`（決定 rebase / skip / 其他）
- `untracked_remote_branch` 且 `relation=diverged`（決定處理方式）
- `branch_behind_origin` 且 `detail.is_current=True`（極罕見：current branch 自己 behind origin；不能用 `git branch -f` 對 current branch 操作，須由使用者選擇 pull / reset / skip）
- 從未 push 的非 well-formed 前綴分支（決定 push / skip）

`unmerged_content_branch` 且 `is_today=True` SHALL 被 /ctx:eod **靜默略過**（不詢問、不警告）。理由：/ctx:eod 可一日多次執行（每段落結束跑一次），當日 content branch 仍在累積中，「觀察前最後把關」是 18:30 cron 的職責，不是 /ctx:eod 的。

#### Scenario: 舊 content 分支詢問是否合併

- **WHEN** 本地有 `content/2026-04-30` 未 merge 至 main，audit 偵測且當日為 2026-05-01
- **THEN** /ctx:eod 詢問「合併 content/2026-04-30 到 main？」並依回應處理

#### Scenario: 當日 content 分支被靜默略過

- **WHEN** /ctx:eod 在 2026-05-01 執行，本地 `content/2026-05-01` 未 merge
- **THEN** /ctx:eod 不詢問、不警告此分支；該分支於 18:30 cron 才會被列入 inbox 提醒

#### Scenario: Diverged 不自動處理

- **WHEN** audit 偵測 `feature/foo` 與 `origin/feature/foo` 雙向 diverged
- **THEN** /ctx:eod 詢問處理方式，不自動 force-push

#### Scenario: untracked_remote_branch[diverged] 詢問處理

- **WHEN** audit 偵測某分支 `untracked_remote_branch` 且 `relation=diverged`
- **THEN** /ctx:eod 詢問使用者處理方式（可選：放棄本地、放棄 origin、手動 rebase 後重跑），不自動處理

#### Scenario: Current branch 自己 behind origin 詢問處理

- **WHEN** current branch 為 `content/2026-05-01`，audit 偵測 `branch_behind_origin` 且 `detail.is_current=True`
- **THEN** /ctx:eod 詢問使用者處理方式（pull --ff-only / reset --hard origin/<branch> / skip），不自動處理（`git branch -f` 對 current branch 會失敗）

### Requirement: 結尾報告

執行結束時 /ctx:eod SHALL 輸出結尾摘要，內容包含：

- 已自動處理項目數
- 仍需手動處理項目數（含原因）
- 結尾狀態：✅ remote 全部最新 / ⚠️ 還有 N 項待處理

#### Scenario: 全清結尾

- **WHEN** /ctx:eod 完整跑完，無未處理項目
- **THEN** 報告以「✅ remote 全部最新」結尾

#### Scenario: 部分處理結尾

- **WHEN** 使用者跳過某些詢問
- **THEN** 報告列出跳過項目，並以「⚠️ 還有 N 項待處理」結尾

### Requirement: 共用 state_audit lib

/ctx:eod SHALL 使用 `infra/periodic_jobs/state_audit/core.py` 的 `audit()` 取得審計報告，不重複實作檢查邏輯。

#### Scenario: 與 cron 共享同一份檢查邏輯

- **WHEN** /ctx:eod 與 cron 在相同 git 狀態下分別執行
- **THEN** 兩者得到語意上等價的 AuditReport（時間戳可不同，findings 集合一致）

### Requirement: Step 3 dirty prompt 在 feature 分支上分支化文案

`/ctx:eod` 在 step 3 偵測到 `dirty_working_tree` finding 時，SHALL 先以 `git branch --show-current` 取得當前分支名。若當前分支前綴為 `feature/`，prompt 文案 SHALL 改寫為「No 是建議路徑（架構變更應留在 feature 分支內 commit），Yes 會嘗試走 /ctx:content（不適合架構工作）」；若前綴非 `feature/`，保留現行通用文案。

#### Scenario: feature 分支上偵測 dirty 時的 prompt 文案

- **WHEN** `/ctx:eod` 在 `feature/add-foo` 分支上偵測到 dirty_working_tree finding
- **THEN** 顯示給使用者的 AskUserQuestion prompt 內容 SHALL 明確包含「No 是建議路徑（架構變更應留在 feature 分支內 commit）」與「Yes 會嘗試走 /ctx:content（不適合架構工作）」這兩段提示文字

#### Scenario: 非 feature 分支上偵測 dirty 時保留現行文案

- **WHEN** `/ctx:eod` 在 `main` 或 `content/2026-05-01` 分支上偵測到 dirty_working_tree finding
- **THEN** 顯示給使用者的 AskUserQuestion prompt SHALL 與現行文案一致（「Yes 轉派 /ctx:content / No 中止」），不含 feature 專屬建議

#### Scenario: prompt 分支判斷不影響後續行為

- **WHEN** 使用者在 feature 分支上看到分支化文案後仍選擇 Yes
- **THEN** `/ctx:eod` SHALL 與現行行為一致地轉派 `/ctx:content`，不在此額外 abort 或攔截

---

### Requirement: feature 分支偵測規則一致

`/ctx:eod` 對 feature 分支的偵測 SHALL 採用「分支名前綴為 `feature/`」的單純規則，與 `/ctx:content` 對 feature 分支的偵測規則保持一致。

#### Scenario: 標準 feature 分支前綴

- **WHEN** 當前分支為 `feature/add-state-audit`
- **THEN** `/ctx:eod` step 3 prompt 應用 feature 文案

#### Scenario: 非 feature 分支前綴

- **WHEN** 當前分支為 `featurex/foo` 或 `topic/feature-foo`
- **THEN** `/ctx:eod` step 3 prompt SHALL NOT 應用 feature 文案（前綴不符 `feature/`）

### Requirement: Protocol 開頭文檔說明 step 排序原則

`.claude/commands/ctx/eod.md` 在 frontmatter 之後、Step 1 之前 SHALL 包含一段文字明確說明 step 排序的 dataflow ordering 原則，內容至少涵蓋：

- 三段語意分組：main mutation（fetch/audit/dirty/合舊 content）、content/today 工作（建分支/bridge-stale update/post-update commit）、push + report
- 不可顛倒的關鍵約束：step 4（合舊 content）必須先於 step 5（建 content/today），否則跨日 EOD 會 fork from stale main

#### Scenario: 文檔存在

- **WHEN** 讀取 `.claude/commands/ctx/eod.md`
- **THEN** 在 frontmatter 與 Step 1 之間 SHALL 包含「Step 排序原則」或等義段落，明確列出三段分組與「step 4 先於 step 5」的約束

### Requirement: Observer-ready hint

執行結束時，若 audit 中**仍**含 `kind == "unmerged_content_branch"` 且 `detail.is_today == True` 的 finding（即當日 content branch 仍未 merge 進 main），/ctx:eod SHALL 在 step 9 結尾報告之後顯示 observer-ready hint，提示使用者：「若已準備好讓 20:00 observer 看到今日工作（收尾、不再追加 commit），請執行 `/ctx:content merge` 將 content/<today> squash 進 main」並說明 /ctx:eod 故意不自動合併 today 的理由（一日多次執行、當日內容仍在累積，merge 是顯式的「我今天結束了」訊號）。

若 today 已合併（無此 finding）或當前不在 content/<today>：SHALL 略過此 step。

#### Scenario: 今日 content 仍未合併時顯示 hint

- **WHEN** /ctx:eod 結束時 audit 仍含 `unmerged_content_branch` 且 `is_today=True`
- **THEN** 在結尾報告下方顯示包含「準備好讓 20:00 observer 看到今日工作 → /ctx:content merge」與「/ctx:eod 故意不自動合併 today」兩段語意的 hint

#### Scenario: 今日 content 已合併時略過 hint

- **WHEN** /ctx:eod 結束時 audit 不含當日 unmerged_content_branch finding
- **THEN** 略過 hint，結尾報告為最後輸出

#### Scenario: 不在 content/today 時略過 hint

- **WHEN** /ctx:eod 結束時當前分支非 content/<today>（例如 abort 在 step 3 時仍在 feature/X）
- **THEN** 略過 hint，結尾報告為最後輸出

### Requirement: Worktree 收尾流程

`/ctx:eod` step 0 對每個活著的 project worktree SHALL 跑收尾流程，依四類規則處理變更後 hard delete worktree。具體步驟：

1. `cd` 到該 worktree
2. `git status --porcelain` 取得 dirty 檔案列表
3. 依路徑 prefix 分類：
   - **類別 1**：`projects/<X>/` 下檔案 → 自動 commit（message 格式 `project(<X>): <auto-generated summary>`，使用者可在互動 prompt 修改）+ push
   - **類別 2**：`contexts/`、`inbox/ideas.md`、`inbox/reading_list.md` → 列入「需搬到 main worktree」清單，SHALL NOT 自動處理
   - **類別 3**：`infra/state/`、`memory/`、`inbox/captured/`、`projects/INDEX.md` → 列入警報清單，SHALL NOT 自動處理
   - **類別 4**：`rules/`、`openspec/`、`.claude/` → 列入警報清單，SHALL NOT 自動處理
4. 若類別 1 有變更：commit + push
5. 若類別 2/3/4 有任何項目：顯示清單給使用者，詢問「保留 worktree 等使用者手動處理？(Y) 還是強制刪除？(N)」——預設 Y（保留以避免遺失工作）
6. 若 step 5 結果為刪除（或無任何 dirty）：執行 `git worktree remove <path>`
7. 累加報告：列入結尾報告的「worktree 收尾」段落

#### Scenario: 純類別 1 變更自動 commit + push + delete

- **WHEN** project worktree 內僅有 `projects/wwpf-qd/PROJECT.md` 與 `projects/wwpf-qd/context/api.md` 變更
- **THEN** 系統 SHALL 自動 commit（提示使用者輸入 message 或採預設）、push 到 `origin/project/wwpf-qd`，然後 `git worktree remove`，無互動詢問

#### Scenario: 類別 1 push 對 newly-created branch 自動加 -u

- **WHEN** project worktree 對應分支（如 `/ctx:project resume` 從 main 重建的 `project/<name>`）尚無 upstream（`git rev-parse --abbrev-ref --symbolic-full-name @{u}` 失敗）
- **THEN** 系統 SHALL 改用 `git push -u origin project/<name>` 建立 upstream tracking，與 Step 8 既有 `no_upstream` auto 規則一致；SHALL NOT 因首次 push 失敗而中止流程或保留 worktree

#### Scenario: 包含類別 2 變更時詢問保留

- **WHEN** project worktree 內含 `projects/wwpf-qd/PROJECT.md` 變更（類別 1）+ `inbox/ideas.md` 變更（類別 2）
- **THEN** 系統 SHALL 自動處理類別 1（commit + push），列出類別 2 檔案，詢問使用者是否保留 worktree

#### Scenario: 包含類別 3 變更時警報並預設保留

- **WHEN** project worktree 內含 `infra/state/system_state.json` 變更
- **THEN** 系統 SHALL 顯示警報「⚠️ system-singleton 檔案在 project worktree 內被修改」，詢問使用者，預設選項為「保留 worktree」（避免誤刪）

#### Scenario: 包含類別 4 變更時警報並預設保留

- **WHEN** project worktree 內含 `rules/SOUL.md` 變更
- **THEN** 系統 SHALL 顯示警報「⚠️ 架構層變更應走 feature/* 分支」，詢問使用者，預設選項為「保留 worktree」

#### Scenario: 乾淨 worktree 直接 hard delete

- **WHEN** project worktree 內無任何變更（`git status --porcelain` 為空）
- **THEN** 系統 SHALL 直接執行 `git worktree remove <path>`，無互動詢問

#### Scenario: Worktree 收尾結果累加進結尾報告

- **WHEN** /ctx:eod 處理完 N 個 project worktree
- **THEN** 結尾報告的「worktree 收尾」段落 SHALL 列出每個 worktree 的處理結果（X 個 commit + push、Y 個 hard delete、Z 個保留待處理）

### Requirement: 結尾報告涵蓋 worktree 收尾結果

`/ctx:eod` 結尾報告 SHALL 在處理過至少一個 project worktree 時包含 worktree 收尾摘要：

- 處理的 project worktree 數量
- 自動 commit + push 的 worktree 數量
- 因類別 2/3/4 變更而保留的 worktree 清單（含原因）
- hard delete 的 worktree 數量

#### Scenario: 全部 worktree 自動清理

- **WHEN** /ctx:eod 處理 3 個 project worktree，全部僅含類別 1 變更
- **THEN** 結尾報告 SHALL 包含 worktree 段落：「處理 3 個 worktree：3 自動 commit + push、3 hard delete、0 保留」

#### Scenario: 部分 worktree 因警報保留

- **WHEN** /ctx:eod 處理 2 個 worktree，其中 1 個有類別 3 警報被保留
- **THEN** 結尾報告 worktree 段落 SHALL 列出該保留 worktree 名稱與保留原因（類別 3：system-singleton 變更）

#### Scenario: 無 worktree 時略過段落

- **WHEN** /ctx:eod 在 step 0 偵測無 spawned worktree（no-op）
- **THEN** 結尾報告 SHALL NOT 包含 worktree 收尾段落
