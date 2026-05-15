# ctx-onboard-command Specification

## Purpose

定義 `/ctx:onboard`（start-of-day）開機總整理命令——使用者主動觸發的早晨 onboarding 工作流，對稱於 `/ctx:eod`。共用 `state_audit.core.audit()` 取 `AuditReport`，與 `/ctx:eod` 和 18:30 cron 共享審計邏輯但 caller policy 不同：onboard 偏 read-only digest（讓使用者快速回到工作狀態），eod 偏 mutation + push（讓 20:00 observer 看到今日工作）。執行流程分兩段——Mutation 段（Step 1–3：fetch → audit → 詢問 dirty 委派 `/ctx:content`，feature 分支 abort），Read 段（Step 4–7：讀昨夜 audit findings、observer 條目分流呈現、active 專案 snapshot、輸出一頁式 digest 與路由建議）。

## Requirements

### Requirement: Command 入口與位置

`/ctx:onboard` 命令 SHALL 定義於 `.claude/commands/ctx/onboard.md`（project-scoped）並使用 `name: ctx:onboard` frontmatter。命令描述 SHALL 表明其用途為「早晨開機後一頁式 digest」並對稱於 `/ctx:eod`。

#### Scenario: 使用者輸入 `/ctx:onboard` 觸發命令
- **WHEN** 使用者於 main 分支、工作樹乾淨的情況下輸入 `/ctx:onboard`
- **THEN** 系統 SHALL 執行 Step 1（`git fetch --all --quiet`）→ Step 2（audit）→ Step 4–7（read 段），跳過 Step 3 dirty handling

#### Scenario: 使用者於 user-scoped 命令未安裝時觸發
- **WHEN** 使用者於 repo 根目錄輸入 `/ctx:onboard`
- **THEN** 系統 SHALL 載入 `.claude/commands/ctx/onboard.md` 而非 user-scoped 版本（user-scoped 不存在）

### Requirement: Step 1 — Git Fetch

命令 SHALL 在 Step 1 執行 `git fetch --all --quiet`，且 fetch 失敗 SHALL NOT 阻斷後續步驟（與 `/ctx:eod` 行為一致）；應於 digest 中顯示「⚠️ fetch 失敗，audit 結果可能反映過時 remote」警告。

#### Scenario: Fetch 成功
- **WHEN** 網路正常
- **THEN** 系統 SHALL 成功執行 `git fetch --all --quiet` 並繼續 Step 2

#### Scenario: Fetch 失敗（網路不通）
- **WHEN** `git fetch --all --quiet` 回傳非 0
- **THEN** 系統 SHALL 列印警告但繼續 Step 2，並於最終 digest 標註「⚠️ fetch 失敗」

### Requirement: Step 2 — 共用 State Audit

命令 SHALL 共用 `infra/periodic_jobs/state_audit/core.audit()` 取得 `AuditReport`，SHALL NOT 重新實作審計邏輯。

#### Scenario: Audit 正常產出 findings
- **WHEN** `state_audit.core.audit()` 成功執行
- **THEN** 系統 SHALL 取得 `AuditReport` 並於後續步驟基於 `report.findings` 做決策

#### Scenario: Audit 模組無法載入
- **WHEN** import 失敗或執行錯誤
- **THEN** 系統 SHALL 中止命令並顯示「state_audit 異常，請檢查 `infra/periodic_jobs/state_audit/`」

### Requirement: Step 3 — Dirty Working Tree 委派處理

若 `report.findings` 含 `kind == "dirty_working_tree"`，命令 SHALL 依當前分支類型分流：

- **`feature/*` 分支**：SHALL 中止 digest 並提示「先 `/opsx:archive` + `/ctx:merge` 收尾架構工作，再跑 `/ctx:onboard`」
- **其他分支**（main、content/*、project/*）：SHALL 用 `AskUserQuestion` 詢問使用者是否委派 `/ctx:content`

ASK 文案 SHALL 明確標明 dirty 來源以 overnight cron 寫入為主，且 SHALL 提供至少兩個選項：`Yes — 委派 /ctx:content`、`No — 繼續 digest，dirty 保持未動`。

#### Scenario: 在 main 分支偵測到 dirty 且使用者選擇 Yes
- **WHEN** 當前分支為 main、工作樹有未提交檔案、使用者於 ASK 中選擇 `Yes`
- **THEN** 系統 SHALL 委派 `/ctx:content`，由其路由矩陣處理 commit；完成後返回繼續 Step 4，工作樹必為乾淨

#### Scenario: 在 main 分支偵測到 dirty 且使用者選擇 No
- **WHEN** 當前分支為 main、工作樹有未提交檔案、使用者於 ASK 中選擇 `No`
- **THEN** 系統 SHALL 繼續 Step 4，並於最終 digest 標註「⚠️ dirty N 個未處理」

#### Scenario: 在 feature 分支偵測到 dirty
- **WHEN** 當前分支前綴為 `feature/`、工作樹有未提交檔案
- **THEN** 系統 SHALL 中止 digest 並顯示提示，SHALL NOT 執行任何 commit 或 fetch 之外的 git 操作

#### Scenario: 工作樹乾淨（dirty 不存在）
- **WHEN** `report.findings` 不含 `kind == "dirty_working_tree"`
- **THEN** 系統 SHALL 跳過 Step 3 直接進入 Step 4

### Requirement: Step 4 — 讀昨晚 State Audit Findings

命令 SHALL 讀取 `inbox/captured/<yesterday>_state_audit.md`（若檔案存在），其中 `<yesterday>` 為當前日期前一日（YYYY-MM-DD 格式）。檔案不存在時 SHALL 跳過此步驟而不報錯。

#### Scenario: 昨日 audit findings 檔案存在
- **WHEN** `inbox/captured/<yesterday>_state_audit.md` 存在
- **THEN** 系統 SHALL 讀取並摘要其內容供 Step 7 digest 引用

#### Scenario: 昨日 audit findings 檔案不存在
- **WHEN** 檔案不存在（昨日 audit 未產生 findings 或 cron 未跑）
- **THEN** 系統 SHALL 靜默跳過此步驟

### Requirement: Step 5 — Observer 條目分流呈現

命令 SHALL 讀取 `memory/OBSERVATIONS.md` 中**最近 3 個 `Date:` block**（reverse-walk，非日期範圍計算——observer 不一定每日跑），並分流為兩類：

- **🔴 Axiom watch**：所有 🔴 High 條目，被動高亮，SHALL NOT 主動建議 propose axiom，SHALL 顯示 reflector 上次跑的時間（讀 `infra/state/system_state.json` 的 `reflector.last_finished_at`）
- **🟡 Skill candidate hints**：由 agent 對最近 3 個 date block 內所有 🟡 條目做**語意判斷**——「這條觀察是否描述一個重複出現、可被封裝成 SOP / skill 的工作流程？」
  - YES：含 SOP / 重複 / 自動化 pattern 描述、明確 step-by-step 流程、或標記 `[工作流/*]`、`[流程/*]`、`[方法論/*]` tag
  - NO：純粹專案進度、技術決策、單次 incident、stale 警示
  - 邊緣：偏保守傾向不列入
  - 命中條目最多顯示 5 條;每條附「考慮 `/opsx:propose skill <agent 推測的 kebab-case 命名>`」軟提示

判斷 SHALL 由 agent 在 session 內進行（已在 onboard 命令執行 context），SHALL NOT spawn subagent 或打外部 API。Agent 偏保守判斷，寧可漏報也不過度提示。

#### Scenario: 最近 3 個 date block 含 🔴 High
- **WHEN** OBSERVATIONS.md 最近 3 個 date block 內含一條或多條 🔴 開頭的觀察
- **THEN** 系統 SHALL 於 digest 的「🔴 Axiom watch」區列出原文（不蒸餾），並附 reflector 上次跑時間

#### Scenario: 條目描述明確的 SOP 化候選
- **WHEN** OBSERVATIONS.md 最近 3 個 date block 內有 🟡 條目描述「重複手動」「應該自動化」「step-by-step 流程」或標記 `[工作流/*]`、`[流程/*]`、`[方法論/*]` tag
- **THEN** Agent SHALL 列入 skill candidate hints 並推導 kebab-case 命名附軟提示

#### Scenario: 條目為單次 incident 或專案進度
- **WHEN** OBSERVATIONS.md 🟡 條目描述純粹是「專案 X 完成 Y」「技術決定 A 而非 B」「stale 警示」這類非工作流敘述
- **THEN** Agent SHALL NOT 列入 skill candidate hints（偏保守，避免過度提示）

#### Scenario: 條目處於邊緣判斷
- **WHEN** 🟡 條目同時含工作流訊號與專案進度敘述
- **THEN** Agent SHALL 偏保守傾向不列入；若列入需於命名後加 `?` 標記表達不確定

#### Scenario: Reflector 已 >10 天未跑
- **WHEN** `system_state.json.reflector.last_finished_at` 距今 >10 天
- **THEN** 系統 SHALL 於 axiom watch 區頂部顯示「⚠️ reflector 已 X 天未跑，請檢查 cron」

#### Scenario: 昨日條目皆為 🟢 Low
- **WHEN** 最近條目皆為 🟢 Low 等級
- **THEN** 系統 SHALL 顯示「無 axiom / skill 候選條目」並繼續 Step 6

### Requirement: Step 6 — 全專案 Snapshot

命令 SHALL 讀取 `projects/INDEX.md` 取得 `status: active` 的專案列表；對每個專案 SHALL 讀取 `projects/<name>/PROJECT.md` 並擷取「下一步」段落（`## 下一步` heading 後的第一段）。輸出 SHALL 為表格格式，欄位包含：name / last_updated / 一行 next-step 摘要 / staleness 旗標（>14 天標 ⚠️）。

#### Scenario: 專案 PROJECT.md 含「下一步」段落
- **WHEN** `projects/<name>/PROJECT.md` 含 `## 下一步` heading
- **THEN** 系統 SHALL 擷取其後第一段非空行作為 next-step 摘要

#### Scenario: 專案 PROJECT.md 缺「下一步」段落
- **WHEN** PROJECT.md 不含 `## 下一步` heading
- **THEN** 系統 SHALL 退回 frontmatter `description` 欄位作為摘要；皆無則顯示「⚠️ PROJECT.md 缺下一步段落」

#### Scenario: 專案 last_updated > 14 天
- **WHEN** INDEX.md 的 `last_updated` 與當日相差 >14 天
- **THEN** 系統 SHALL 於該行標 ⚠️ staleness 旗標

#### Scenario: 無 active 專案
- **WHEN** `projects/INDEX.md` 中無 `status: active` 條目
- **THEN** 系統 SHALL 顯示「目前無 active 專案」並繼續 Step 7

### Requirement: Step 6.5 — Inbox Reconciliation

命令 SHALL 在 Step 6（全專案 snapshot）完成後、Step 7（digest 輸出）開始前執行 Step 6.5 Inbox Reconciliation：讀取 `inbox/todos.md` Active 區段與 `inbox/ideas.md` 全部內容，對照下列證據來源，輸出 0–N 條 reconciliation 建議於 Step 7 digest：

1. Step 2 audit findings
2. Step 6 project snapshot（含 last_updated）
3. 最近 30 天 `git log --oneline`
4. 最近 30 天 `openspec/changes/archive/` 目錄列表

每條建議 SHALL 屬於以下 4 類之一，並使用對應 emoji 標記：

- **✅ 看似已完成**（todos）：條目敘述對應的工作有明確完成證據（archive、commit、audit ok 連續多日），建議 mark `[x]`
- **🔄 事實已變**（todos）：條目描述跟現況不符（依賴改、架構改、依據已不存在），建議重寫或刪除
- **🟢 前置就緒**（todos）：條目明示前置條件且該前置已滿足，提示「前置已就緒，可開始」
- **📦 已演化**（ideas）：idea 標題 / 描述跟某 archived change 高度重疊，建議移除或註明已歸檔為 `<change-name>`

每類顯示上限 3 條，4 類合計上限 8 條；超過上限時 SHALL 顯示「…及 N 條，跑 /opsx:propose 處理」摺疊提示。

所有建議 SHALL 使用弱措辭（「→ 建議 X」「→ 看似 Y」格式），不使用「必須」「應該」等強制語氣；user 最終裁決，命令 SHALL NOT 詢問是否套用建議、SHALL NOT 自動編輯 inbox 檔案。

判定邊緣（證據不充分）時 SHALL 不顯示該條目（保守偏向：漏報 > 誤報）。

語意判斷 SHALL 在 session 內完成（同 Step 5.3 skill candidate hint 模式），SHALL NOT spawn subagent、SHALL NOT 打外部 LLM API。

#### Scenario: todos.md 條目對應的工作已完成
- **WHEN** `inbox/todos.md` Active 含「修復 ai_heartbeat capture pipeline」條目，且最近 30 天 git log 顯示 cc-hooks-capture 相關 commit 已取代該 capture 機制
- **THEN** Step 7 digest 在 Inbox reconciliation 區塊顯示一條 ✅ 或 🔄 建議，引用該 commit 證據

#### Scenario: idea 已演化成 archived change
- **WHEN** `inbox/ideas.md` 含「Heptabase 串接」idea，且 `openspec/changes/archive/` 內存在 `<date>-heptabase-ingest-pipeline` 目錄
- **THEN** Step 7 digest 在 Inbox reconciliation 區塊顯示 📦 建議，引用該 archived change 名稱

#### Scenario: todo 前置條件已從現況看到就緒
- **WHEN** todo 條目寫明「前置：add-cc-hooks-capture archive 完成」，且該 change 已於 `openspec/changes/archive/` 出現
- **THEN** Step 7 digest 顯示 🟢 建議「前置已就緒」

#### Scenario: 無 reconciliation 命中
- **WHEN** 所有 inbox 條目對照證據後皆未命中 4 類條件
- **THEN** Step 7 digest SHALL NOT 顯示「📌 Inbox reconciliation」段落（整段省略，不寫「✅ 無建議」）

#### Scenario: 命中超過顯示上限
- **WHEN** 4 類合計命中 12 條建議
- **THEN** digest 顯示前 8 條（每類最多 3 條依序填滿），尾端附「…及 4 條，跑 /opsx:propose 處理」摺疊提示

#### Scenario: reading_list.md 不納入對照
- **WHEN** Step 6.5 執行時
- **THEN** 命令 SHALL NOT 讀取或對照 `inbox/reading_list.md`

#### Scenario: 命令不修改 inbox 檔案
- **WHEN** reconciliation 產出 N 條建議
- **THEN** 命令 SHALL NOT 對 `inbox/todos.md` 或 `inbox/ideas.md` 執行任何寫入操作

### Requirement: Step 7 — 一頁式 Digest 與路由建議

命令 SHALL 在 Step 7 輸出單一 digest 訊息，包含以下區段（順序固定）：

1. 系統狀態徽章（fetch 結果、audit findings 摘要、role failures 摘要）
2. 昨夜 observer 重點（🔴 Axiom watch + 🟡 Skill candidate hints）
3. 全專案 snapshot 表格
4. **📌 Inbox reconciliation**（Step 6.5 產出之 0–N 條建議；零提示時整段省略）
5. 路由建議清單（至少包含「挑專案推進 → `/ctx:project load <name>`」、「SOP 化某流程 → `/opsx:propose skill <name>`」）

系統狀態徽章區 SHALL 在 audit findings 含至少一個 `kind=role_failed_run` 時新增一行 `🔥 role failures: …`，列出失敗的 role 名稱與 `last_finished_at` 摘要（例如 `heptabase_ingest（last failed 2026-05-06）`）；多個 role 失敗時以逗號分隔。當無 `role_failed_run` finding 時 SHALL NOT 顯示此行。

`role_failed_run` findings 已在徽章區呈現後 SHALL NOT 重複列在「📋 昨日 audit findings」段落，避免雙重曝光稀釋訊號。其他 finding kind（如 `dirty_working_tree` / `stale_active_project_bridge` 等）的呈現規則不變。

Digest SHALL 不超過一頁可視範圍（建議 < 60 行）；SHALL NOT 嵌入 OBSERVATIONS.md 全文，只顯示符合分流規則的條目原文片段。

#### Scenario: 全部步驟成功完成
- **WHEN** Step 1–6.5 皆成功
- **THEN** 系統 SHALL 輸出一頁式 digest 並結束命令，SHALL NOT 自動執行任何路由建議

#### Scenario: Digest 輸出後使用者選擇路由
- **WHEN** 使用者讀完 digest 後手動輸入路由建議中的某個指令
- **THEN** 系統 SHALL 由該指令獨立處理，與 `/ctx:onboard` 解耦

#### Scenario: 徽章區呈現 role failures
- **WHEN** audit findings 含 `kind=role_failed_run`、`detail.role=heptabase_ingest`、`detail.last_finished_at=2026-05-06T23:00:02+08:00`
- **THEN** digest 系統狀態徽章區含一行 `🔥 role failures: heptabase_ingest（last failed 2026-05-06）`

#### Scenario: 多 role 失敗時逗號分隔
- **WHEN** audit findings 含兩個 `role_failed_run`，`detail.role` 分別為 `heptabase_ingest` 與 `observer`
- **THEN** digest 徽章區的 `🔥 role failures` 行同時列出兩個 role 名稱，以逗號分隔

#### Scenario: 無 role failures 時不顯示徽章行
- **WHEN** audit findings 不含任何 `role_failed_run`
- **THEN** digest 徽章區 SHALL NOT 顯示 `🔥 role failures` 行

#### Scenario: role_failed_run 不重複出現在 findings 段落
- **WHEN** audit findings 含 `role_failed_run` 與 `dirty_working_tree`
- **THEN** 「📋 昨日 audit findings」段落僅列出 `dirty_working_tree`（`role_failed_run` 已在徽章區呈現）

#### Scenario: Inbox reconciliation 區塊位於全專案 snapshot 與路由建議之間
- **WHEN** Step 6.5 產出至少 1 條建議
- **THEN** digest 輸出順序 SHALL 為：徽章 → observer 重點 → 全專案 snapshot → 📌 Inbox reconciliation → 路由建議

### Requirement: Guardrails

命令 SHALL 遵守以下不變式：

- SHALL NOT 自動 commit 任何檔案（Step 3 透過委派 `/ctx:content` 才會 commit）
- SHALL NOT 自動 push 任何分支
- SHALL NOT 自動切換到非當前分支（Step 3 委派 `/ctx:content` 由其自身的路由矩陣處理切換）
- SHALL NOT spawn subagent 或打額外外部 API（agent 在 session 內讀檔做語意判斷如 Step 5.3 / Step 6.5 OK，因為已在現有 session context、零增量成本）
- SHALL NOT 修改 `memory/OBSERVATIONS.md`、`rules/`、`projects/<name>/PROJECT.md`、`inbox/todos.md`、`inbox/ideas.md` 等讀取來源
- SHALL 對所有讀檔操作做存在性檢查，檔案不存在時優雅降級而非報錯

#### Scenario: 命令誤觸發 commit
- **WHEN** 命令邏輯內含任何 `git add` / `git commit` / `git push` 直接呼叫
- **THEN** 此違反 guardrail，SHALL 透過 code review 發現並修正（屬實作 invariant）

#### Scenario: 讀取來源檔案不存在
- **WHEN** `inbox/captured/<yesterday>_state_audit.md`、`memory/OBSERVATIONS.md`、`projects/INDEX.md`、`inbox/todos.md`、`inbox/ideas.md` 任一不存在
- **THEN** 系統 SHALL 顯示「⚠️ 缺 <檔案名>，跳過該段」並繼續其他步驟，SHALL NOT 中止命令

#### Scenario: 命令誤編輯 inbox 檔案
- **WHEN** 命令邏輯內含對 `inbox/todos.md` 或 `inbox/ideas.md` 的寫入操作
- **THEN** 此違反 guardrail，Step 6.5 reconciliation 必須只讀

### Requirement: Step 7 digest 顯示 worktree 狀態

`/ctx:onboard` Step 7 digest 的「系統狀態徽章」段落 SHALL 顯示活著的 project worktree 數量（若有任一條 `git worktree list` 中 `.claude/worktrees/<name>` 路徑）。若有 stale worktree（前一日 EOD 未清理乾淨而保留的 worktree）SHALL 顯示警告。

無 spawned worktree 時 SHALL NOT 顯示相關徽章行。

#### Scenario: 徽章顯示 worktree 數量

- **WHEN** `/ctx:onboard` 偵測 `git worktree list` 顯示 2 個 `.claude/worktrees/<name>` 條目
- **THEN** digest 系統狀態徽章 SHALL 包含一行 `🌳 active worktrees: 2 (wwpf-qd, yoga-cs-agent)`

#### Scenario: 前一日未收尾的 stale worktree 警告

- **WHEN** `/ctx:onboard` 偵測到 worktree 路徑存在但其分支對應的 PROJECT.md `last_updated` 距今 >1 天（隱含前次 EOD 未走完收尾或被使用者保留）
- **THEN** digest SHALL 顯示警告「⚠️ N 個未收尾的 worktree，下次 /ctx:eod 會一併處理」並列出名稱

#### Scenario: 無 worktree 時不顯示徽章

- **WHEN** `/ctx:onboard` 偵測無 spawned worktree
- **THEN** digest 徽章 SHALL NOT 包含 worktree 相關行

### Requirement: Step 7 路由建議含 spawn 提示

當 Step 6 全專案 snapshot 列出至少一個 active project 時，Step 7 的「路由建議清單」SHALL 包含 spawn worktree 提示「挑專案推進 → `/ctx:project resume <name>`（自動 spawn worktree）」。

#### Scenario: 路由建議含 spawn 提示

- **WHEN** `/ctx:onboard` Step 6 顯示有 active project
- **THEN** Step 7 路由建議 SHALL 包含「挑專案推進 → `/ctx:project resume <name>`（自動 spawn worktree）」一行
