# state-audit Specification

## Purpose

定義 state_audit 角色——一個無 LLM 依賴的純規則狀態審計，與 ai_heartbeat 平行存在。負責偵測 git 工作樹、未合併分支、bridge-stale 專案、未推 push、main 落後 origin 五類狀況，產出結構化 `AuditReport` 供 cron 18:30 silent backstop 與 `/ctx:eod` 互動命令共用。設計目標是把「規則性判斷」從「需要 LLM 的角色」拆出來，獨立測試、獨立部署、獨立失敗。
## Requirements
### Requirement: state_audit 角色獨立於 ai_heartbeat

系統 SHALL 提供 `infra/periodic_jobs/state_audit/` 作為與 `ai_heartbeat/` 平行的角色，無 LLM 或外部 API 依賴，僅依賴 Python 標準庫與 `git` CLI。

#### Scenario: 無 LLM 依賴可獨立執行

- **WHEN** 在無 `ANTHROPIC_API_KEY`、無 OpenCode Server 的環境執行 state_audit cron 或 lib
- **THEN** 正常完成審計，不拋出依賴缺失錯誤

#### Scenario: 與 ai_heartbeat 解耦

- **WHEN** ai_heartbeat 模組被移除或失效
- **THEN** state_audit 仍可獨立 import 與執行，不傳遞性依賴

### Requirement: core.audit() 提供共用檢查函式

`state_audit.core` SHALL 暴露 `audit() -> AuditReport` 函式，供 `cron.py` 與 `/ctx:eod` 命令共用。`AuditReport` SHALL 包含 `timestamp`、`branch`、`findings: list[Finding]` 三個欄位。

#### Scenario: 執行 audit() 取得結構化報告

- **WHEN** 呼叫 `state_audit.core.audit()`
- **THEN** 回傳 `AuditReport` 物件，`findings` 為 0 或多個 `Finding`

#### Scenario: 同一 audit() 可被多個 caller 重複呼叫

- **WHEN** 同一 process 內 `audit()` 被呼叫兩次
- **THEN** 第二次呼叫不依賴第一次的 side effect，獨立完成

### Requirement: 執行五項檢查

`audit()` SHALL 執行以下五項檢查並產出對應 `Finding`（找到時）：

1. **dirty_working_tree**：`git status --porcelain` 非空
2. **unmerged_content_branch**：本地存在 `content/YYYY-MM-DD` 分支，且其 HEAD commit 不在 main 的祖先鏈。`detail` SHALL 含 `is_today: bool`（YYYY-MM-DD 是否等於系統當前日期），讓 caller 套用各自 policy
3. **stale_active_project_bridge**：對 `projects/INDEX.md` 中 `status: active` 的每個 `<name>`，若 `projects/<name>/PROJECT.md` 的 git mtime > `contexts/work_logs/` 中所有 `*<name>_update.md` 與 `*<name>_retrospective.md` 的最新 git mtime
4. **本地與 remote 分支關係檢查**（單一檢查產出兩類 finding）：對每個本地分支：
   - 若有 `@{upstream}` 設定：依 ahead/behind 產出既有 `unpushed_branch` 相關 findings（kind 包含 `no_upstream` *作為 kind ── 見下* / `ahead_of_upstream` / `diverged_from_upstream`）
   - 若**無** `@{upstream}` 但 `git rev-parse --verify refs/remotes/origin/<branch>` 成功（remote ref 已存在於 fetch 過的本地 cache）：產出新 finding kind `untracked_remote_branch`，`detail.relation` SHALL 為 `equal | ahead | behind | diverged` 之一（local commit 與 origin/<branch> 的關係），`detail.branch` SHALL 為分支名
   - 若**無** `@{upstream}` 且 remote ref 也不存在：產出 `no_upstream` finding（既有行為，從未 push 的全新分支）
   - 本檢查 SHALL 假定 caller 已執行 `git fetch --all`，不重複 fetch；`refs/remotes/origin/<branch>` 的新鮮度由 caller 負責
5. **branch_behind_origin**：對每個本地分支 `<branch>`（含 main），若 `<branch>` 的 ahead=0 且 behind>0（相對 `origin/<branch>`）SHALL 產出 `branch_behind_origin` finding。`detail` SHALL 含 `branch: str`、`behind_count: int`、`is_current: bool`（是否為 current branch，影響下游處置策略）

#### Scenario: 髒檔被偵測

- **WHEN** 工作樹有未提交變更，呼叫 audit()
- **THEN** AuditReport 含 `kind=dirty_working_tree` 的 Finding

#### Scenario: Bridge-stale 專案被偵測

- **WHEN** 某 active 專案的 PROJECT.md 在最近一次 `<name>_update.md` 之後被 commit
- **THEN** AuditReport 含 `kind=stale_active_project_bridge`、`detail.project_name=<name>` 的 Finding

#### Scenario: 從未 push 的全新分支被偵測

- **WHEN** 本地存在 `content/2026-05-01` 分支，無 upstream，且 `refs/remotes/origin/content/2026-05-01` 不存在
- **THEN** AuditReport 含 `kind=no_upstream`、`detail.branch=content/2026-05-01` 的 Finding

#### Scenario: Remote 已存在但本地無 tracking 被偵測（equal）

- **WHEN** 本地存在 `project/foo` 分支，無 upstream，`refs/remotes/origin/project/foo` 存在且與本地 HEAD 同 SHA
- **THEN** AuditReport 含 `kind=untracked_remote_branch`、`detail.branch=project/foo`、`detail.relation=equal` 的 Finding

#### Scenario: Remote 已存在但本地無 tracking 被偵測（ahead）

- **WHEN** 本地存在 `feature/bar` 分支，無 upstream，`refs/remotes/origin/feature/bar` 存在且為本地 HEAD 的祖先（local 領先）
- **THEN** AuditReport 含 `kind=untracked_remote_branch`、`detail.relation=ahead` 的 Finding

#### Scenario: Remote 已存在但本地無 tracking 被偵測（behind）

- **WHEN** 本地存在 `project/qheart-ap` 分支，無 upstream，本地 HEAD 為 `refs/remotes/origin/project/qheart-ap` 的祖先（local 落後）
- **THEN** AuditReport 含 `kind=untracked_remote_branch`、`detail.relation=behind` 的 Finding

#### Scenario: Remote 已存在但本地無 tracking 被偵測（diverged）

- **WHEN** 本地存在某分支，無 upstream，與 `refs/remotes/origin/<branch>` 雙向都有對方沒有的 commit
- **THEN** AuditReport 含 `kind=untracked_remote_branch`、`detail.relation=diverged` 的 Finding

#### Scenario: Diverged 分支被偵測（已設 upstream）

- **WHEN** 本地分支與 upstream 雙向都有對方沒有的 commit
- **THEN** AuditReport 含 `kind=diverged_from_upstream` 的 Finding

#### Scenario: Main 落後 origin 被偵測為通用 branch_behind_origin

- **WHEN** `git fetch --all` 後，`origin/main` 領先 local main 兩個 commit，且 current branch 為 `content/2026-05-01`
- **THEN** AuditReport 含 `kind=branch_behind_origin`、`detail.branch=main`、`detail.behind_count=2`、`detail.is_current=False` 的 Finding

#### Scenario: 非 main 分支落後 origin 被偵測

- **WHEN** `origin/project/qheart-ap` 領先本地 `project/qheart-ap` 兩個 commit，current branch 為 `content/<today>`
- **THEN** AuditReport 含 `kind=branch_behind_origin`、`detail.branch=project/qheart-ap`、`detail.is_current=False` 的 Finding

#### Scenario: Current branch 自己 behind origin 被偵測

- **WHEN** current branch 為 `content/2026-05-01`，`origin/content/2026-05-01` 領先本地一個 commit
- **THEN** AuditReport 含 `kind=branch_behind_origin`、`detail.branch=content/2026-05-01`、`detail.is_current=True` 的 Finding

#### Scenario: 全乾淨時 findings 為空

- **WHEN** 工作樹乾淨、無未 merged content/*、無 bridge-stale 專案、所有分支 push 與 upstream 一致、無分支落後 origin
- **THEN** AuditReport 的 `findings` 為空 list（仍寫入 raw_signals 證明 audit 跑過）

### Requirement: cron 進入點為 silent backstop

`state_audit.cron` SHALL 為無人值守進入點，符合以下行為：

- 開頭執行 `git fetch --all`
- 執行 `core.audit()`
- 若 `findings` 非空：寫 `inbox/captured/<YYYY-MM-DD>_state_audit.md`（人類可讀的摘要）
- 無論 findings 是否為空：寫 `raw_signals/<YYYY-MM-DD>/state_audit.json`（AuditReport 序列化）
- SHALL NOT 主動通知（push notification / email），僅寫檔
- SHALL NOT 嘗試自動修復（不 push、不 commit、不切分支）

cron 寫入的 inbox 摘要 SHALL 將 unmerged content/* 全數列出（含 `is_today=True` 的當日分支），並對 `is_today=True` 的分支採用「observer 前最後把關」的 prose 提醒，與遺留分支區隔。

#### Scenario: 狀態不乾淨時寫 inbox 證據

- **WHEN** cron 執行且 audit 找到 findings
- **THEN** `inbox/captured/<date>_state_audit.md` 被寫入，內容包含每個 finding 的可讀描述

#### Scenario: content/today 未合併時 cron 明示提醒

- **WHEN** cron 在 18:30 執行，本地 `content/<today>` 存在且未 merge 至 main
- **THEN** inbox 摘要含明示提醒（語意如「observer 即將於 20:00 執行，content/<today> 尚未合併」），與「content/<earlier> 遺留」區隔

#### Scenario: 狀態乾淨時仍寫 raw_signals

- **WHEN** cron 執行且 findings 為空
- **THEN** `raw_signals/<date>/state_audit.json` 被寫入（含空 findings 陣列），但 `inbox/captured/` 不寫

#### Scenario: cron 不修改 git 狀態

- **WHEN** cron 完整執行
- **THEN** `git status` 與執行前相同（不含暫存變更、不含 commit、不含分支切換、不含 push）

### Requirement: 寫 raw_signals 採用 atomic write

寫 `raw_signals/<date>/state_audit.json` 與 `inbox/captured/<date>_state_audit.md` SHALL 使用「先寫到 `.tmp` 後 rename」的 atomic 模式，避免 19:00 capture 與 18:30 state_audit 的時序競爭產生 partial file。

#### Scenario: 寫入過程被中斷

- **WHEN** state_audit 寫到一半被 SIGKILL
- **THEN** `raw_signals/<date>/state_audit.json` 要嘛不存在、要嘛是完整有效的 JSON

### Requirement: 五項檢查的 git mtime 比較使用 git log

`stale_active_project_bridge` 的時間比較 SHALL 使用 git log 取得 commit time，而非 filesystem mtime，以避免多機 clone 後 mtime 失真。

#### Scenario: Clone 後 mtime 不影響判定

- **WHEN** 在新 clone 的 repo 上執行 audit
- **THEN** bridge-stale 判定基於 git history 而非 fs mtime，結果與舊 clone 一致

### Requirement: 偵測 missed observer/reflector run

`audit()` SHALL 額外檢查前一天（yesterday）的 `raw_signals/<yesterday>/observer_run.json` 與 `raw_signals/<yesterday>/reflector_run.json`（reflector 為週執行，檢查邏輯依 reflector 排程週期）的存在性。若 observer 預期跑而沒跑，SHALL 產出 `kind=missed_observer_run` 的 Finding；reflector 同理產出 `kind=missed_reflector_run`。Finding 的 `detail` SHALL 含 `expected_date: str`（缺跑的目標日期）；`suggested_action` SHALL 提供補跑指令字串。

reflector 部分的判斷依據 `_read_state_roles()` 取得 `roles.reflector.last_finished_at`；該讀取 SHALL 透過 `_read_state_roles()` 的標準 source authority 機制（default 從 `origin/main` 讀，失敗 fallback working tree），確保跨分支執行時不會看到 stale state。

#### Scenario: 偵測 observer 昨天沒跑

- **WHEN** today=2026-05-02，且 `raw_signals/2026-05-01/observer_run.json` 不存在
- **THEN** AuditReport 含 `kind=missed_observer_run`、`detail.expected_date=2026-05-01` 的 Finding，`suggested_action` 含補跑指令

#### Scenario: observer 昨天有跑則不產出 missed-run finding

- **WHEN** today=2026-05-02，且 `raw_signals/2026-05-01/observer_run.json` 存在且 status=ok
- **THEN** AuditReport 不含 `missed_observer_run` finding

#### Scenario: 不檢查 today 的 missed run

- **WHEN** today=2026-05-02 且 state_audit cron 在 18:30 跑（observer 排程於 20:00）
- **THEN** 即使 `raw_signals/2026-05-02/observer_run.json` 不存在，AuditReport 不產出 `missed_observer_run`（避免時序競爭）

#### Scenario: reflector 為週執行

- **WHEN** reflector last_finished_at 距今超過 8 天（暗示上週應該跑而沒跑）
- **THEN** AuditReport 含 `kind=missed_reflector_run` 的 Finding，`detail.last_finished_at=<ISO>` 與補跑指令

#### Scenario: feature/* 分支跑 audit 不誤報 missed_reflector_run

- **WHEN** caller 在 `feature/<name>` 分支跑 audit，origin/main 上的 `system_state.json` 含 `reflector.last_finished_at` 在 staleness threshold 之內
- **THEN** AuditReport 不含 `missed_reflector_run`（即使 working tree 視角的 system_state 是 stale）

### Requirement: state_audit 從 origin/main 讀 system_state.json

`_read_state_roles()` SHALL 從 `origin/main` ref 讀 `infra/state/system_state.json`（透過 `git show origin/main:infra/state/system_state.json`），而非從 working tree。這保證 audit 結果反映 authoritative remote state，避免 cross-branch divergence。

`_read_state_roles()` SHALL 接受 `ref: str | None` 參數，預設 `"origin/main"`。當 `ref=None` 時 SHALL 讀 working tree 的 `infra/state/system_state.json`（保留舊行為，供測試與顯式覆蓋使用）。

#### Scenario: ref=origin/main 成功讀取

- **WHEN** `_read_state_roles(ref="origin/main")` 呼叫且 `git show origin/main:infra/state/system_state.json` 成功
- **THEN** 回傳該 ref 上 system_state.json 的 `roles` 欄位內容

#### Scenario: ref=None 顯式讀 working tree

- **WHEN** `_read_state_roles(ref=None)` 呼叫
- **THEN** 系統 SHALL 讀 working tree 的 `infra/state/system_state.json`，不執行任何 git subprocess

#### Scenario: 使用 default ref

- **WHEN** `_read_state_roles()` 不帶 `ref` 參數呼叫
- **THEN** 等同於 `ref="origin/main"`

### Requirement: state read 失敗時 silent fallback 至 working tree

當 `_read_state_roles()` 嘗試從非 None 的 `ref` 讀失敗（git subprocess 非 0 exit code、超時、或 stdout 不是合法 JSON）時，SHALL silent fallback 到讀 working tree，並透過 `logger.warning()` 記錄一條 trace。SHALL NOT 產出 audit `Finding`。

#### Scenario: origin/main ref 不存在（fresh clone 未 fetch）

- **WHEN** `_read_state_roles(ref="origin/main")` 呼叫且 `git show origin/main:...` 因 ref 不存在而失敗
- **THEN** 系統 SHALL 寫一條 `logger.warning`、改讀 working tree 路徑，回傳該結果（空 dict 若 working tree 也無檔）
- **AND** 不產出 `Finding`，audit 報告不污染

#### Scenario: git subprocess 超時

- **WHEN** `git show origin/main:...` 超過 5 秒未返回
- **THEN** 系統 SHALL 終止 subprocess、寫 `logger.warning`、fallback 到 working tree

#### Scenario: stdout 非合法 JSON

- **WHEN** `git show` 成功但 stdout 解析 JSON 失敗
- **THEN** 系統 SHALL 寫 `logger.warning` 並 fallback 到 working tree

### Requirement: audit() 契約要求 caller 必須先 fetch

`audit()` 的 docstring SHALL 明確說明 caller MUST 在呼叫前執行 `git fetch`，否則 `origin/main` 為 stale state 時可能產生 false `missed_reflector_run` 等 finding。docstring SHALL 列出當前合規 caller（`cron.py` 透過 `_fetch_all()`、`/ctx:eod` step 1）。

#### Scenario: cron silent backstop

- **WHEN** `cron.py` 進入 `main()` 並呼叫 `audit()`
- **THEN** 在呼叫前 SHALL 已執行 `_fetch_all()`（current behavior）

#### Scenario: /ctx:eod 互動命令

- **WHEN** `/ctx:eod` 呼叫 `audit()`
- **THEN** Step 1 SHALL 已跑 `git fetch --all`（current behavior）

### Requirement: state_audit 寫 run log

`state_audit/cron.py` 在完成審計後 SHALL 寫 `raw_signals/<date>/state_audit_run.json`（同 system-state-coordination spec 中的 run log schema）並更新 `infra/state/system_state.json` 的 `state_audit` 角色區段。

#### Scenario: state_audit 完成寫 run log

- **WHEN** state_audit cron 成功完成 audit() 與寫 raw_signals/<date>/state_audit.json
- **THEN** `raw_signals/<date>/state_audit_run.json` 與 system_state.json 中 state_audit 區段同步更新，status=ok

### Requirement: 偵測 role failed run

`audit()` SHALL 透過 `_read_state_roles()` 取得 `infra/state/system_state.json` 的 `roles` dict，對其中每個 `role_name` 檢查 `roles[role_name].last_status`。若該值為字串 `"failed"`，SHALL 產出一個 `kind=role_failed_run` 的 Finding。

每個 `role_failed_run` finding 的 `detail` SHALL 含：

- `role: str` — 失敗的 role 名稱（即 `roles` dict 的 key）
- `last_finished_at: str | None` — `roles[role_name].last_finished_at` 的原值（缺欄位則為 None）
- `last_target_date: str | None` — `roles[role_name].last_target_date` 的原值（缺欄位則為 None）

`suggested_action` SHALL 透過模組級 `ROLE_RECOVERY_HINTS: dict[str, str]` 查表：

- 已知 role（含 `heptabase_ingest`、`observer`、`reflector`）SHALL 回對應的 bespoke 提示字串
- 未知 role SHALL 回 generic fallback 字串（語意如「請查 `raw_signals/<date>/<role>_run.json` 以取得失敗詳情」）

`severity` SHALL 為 `"warn"`，與既有 `missed_observer_run` / `missed_reflector_run` 同級。

`role_failed_run` 檢查 SHALL 與 `_check_missed_runs` 解耦（不在同一函式內），保持單一職責。

#### Scenario: 單一 role 失敗時被偵測

- **WHEN** `system_state.json` 的 `roles.heptabase_ingest.last_status == "failed"`，且 `last_finished_at == "2026-05-06T23:00:02+08:00"`
- **THEN** AuditReport 含 `kind=role_failed_run`、`detail.role=heptabase_ingest`、`detail.last_finished_at=2026-05-06T23:00:02+08:00`、`severity=warn` 的 Finding，且 `suggested_action` 為 heptabase_ingest 對應的 bespoke 提示

#### Scenario: 多個 role 同時失敗時各自產出 finding

- **WHEN** `roles.heptabase_ingest.last_status == "failed"` 且 `roles.observer.last_status == "failed"`
- **THEN** AuditReport 含兩個 `kind=role_failed_run` 的 Finding，`detail.role` 分別為 `heptabase_ingest` 與 `observer`

#### Scenario: 全部 role 為 ok 時不產出 finding

- **WHEN** `system_state.json` 中所有 role 的 `last_status` 皆為 `"ok"`
- **THEN** AuditReport 不含 `role_failed_run` finding

#### Scenario: role 缺 last_status 欄位時 graceful skip

- **WHEN** `roles.foo` 存在但無 `last_status` 鍵（例如剛初始化的角色）
- **THEN** 該 role SHALL 不產出 `role_failed_run` finding，audit() 不 raise exception

#### Scenario: 未知 role 失敗時用 generic fallback hint

- **WHEN** `roles.new_pipeline.last_status == "failed"` 且 `new_pipeline` 不在 `ROLE_RECOVERY_HINTS` dict 內
- **THEN** finding 的 `suggested_action` 為 generic fallback 字串（含「查 `raw_signals/<date>/new_pipeline_run.json`」字樣）

#### Scenario: last_status 為 running 時不產出 role_failed_run

- **WHEN** `roles.observer.last_status == "running"`（仍在跑或卡死）
- **THEN** AuditReport 不含 `kind=role_failed_run`、`detail.role=observer` 的 Finding（卡死偵測不在本檢查範圍）

#### Scenario: state read 失敗時不誤報

- **WHEN** `_read_state_roles()` 因 fallback 路徑失敗回傳空 dict
- **THEN** AuditReport 不含任何 `role_failed_run` finding（沒有資料來源就不報）

### Requirement: 偵測 stale running role

`state_audit.core` SHALL 提供 `_check_stale_running_role` 檢查：scan `system_state.json` 的 `roles.*`，當任一 role 的 `last_status == "running"` 且 `last_started_at` 距今超過閾值（預設 2 小時，可由環境變數 `STATE_AUDIT_RUNNING_THRESHOLD_HOURS` 覆寫）時，emit 一筆 `stale_running_role` finding。finding `detail` 至少包含 `role`、`last_started_at`、`last_target_date`、`elapsed_hours`、`threshold_hours`。

`role-failed-run` 與 `stale_running_role` 共用 `ROLE_RECOVERY_HINTS` 表，已知 role（observer / capture / triage_stage1 / triage_stage2 / reflector）SHALL 提供 bespoke recovery hint，未知 role fallback 到 generic hint。observer 的 hint MUST 顯式警示「不要對 `infra/state/system_state.json` 跑 `git checkout --` 直接 revert——running 狀態可能對應未收尾的真實 cron 工作」。

#### Scenario: Role 卡 running 超過閾值

- **WHEN** `system_state.json` 中某 role 的 `last_status="running"` 且 `last_started_at` 為 3 小時前（超過預設 2h 閾值）
- **THEN** audit 報告含一筆 `kind="stale_running_role"` 的 finding，detail 含該 role 名與 elapsed_hours，severity 為 `warn`

#### Scenario: Role 卡 running 但未過閾值

- **WHEN** `system_state.json` 中某 role 的 `last_status="running"` 且 `last_started_at` 為 30 分鐘前（未超過預設 2h 閾值）
- **THEN** audit 報告 SHALL NOT 為此 role emit `stale_running_role` finding（避免誤觸正在執行的 long-running cron）

#### Scenario: Threshold 由環境變數覆寫

- **WHEN** 環境變數 `STATE_AUDIT_RUNNING_THRESHOLD_HOURS=0.5` 被設定，且某 role 卡 running 已 1 小時
- **THEN** audit 以 0.5h 為閾值判斷，emit `stale_running_role` finding

#### Scenario: 多 role 同時卡 running

- **WHEN** observer 與 capture 同時 `last_status="running"` 且兩者皆超過閾值
- **THEN** audit 報告含兩筆 `stale_running_role` findings，每筆對應一個 role

#### Scenario: Observer stale 顯式警示 revert

- **WHEN** observer 卡 running 觸發 `stale_running_role`，consumer 透過 `ROLE_RECOVERY_HINTS` 取 hint
- **THEN** 回傳的 hint 文字 MUST 包含手動補跑指令與「不要對 system_state.json 做 git checkout -- revert」的警示
### Requirement: 偵測 stale heptabase inbox backlog

`audit()` SHALL 額外執行 `stale_heptabase_inbox` 檢查：scan `inbox/captured/heptabase/<bucket>/*.md`（bucket ∈ {github, article, youtube, threads}），對每個檔名解析日期（pattern `YYYY-MM-DD.md`），找出最舊日期 `oldest_date`。若 `today - oldest_date > 7 天` SHALL 產出一個 `kind=stale_heptabase_inbox` 的 Finding。

Finding 的 `detail` SHALL 含：

- `oldest_date: str` — 最舊未處理 day-file 的日期（YYYY-MM-DD）
- `days_behind: int` — `today - oldest_date` 的天數
- `total_day_files: int` — 目前 inbox 內 day-files 總數（含所有 bucket）

`severity` SHALL 為 `"warn"`，與 `missed_observer_run` 同級。

`suggested_action` SHALL 為固定字串，語意如「執行 `/inbox:digest stale` 開始消化 backlog」。

檢查 SHALL 不依賴 LLM 或外部 API；SHALL 僅讀本地 filesystem。

#### Scenario: 最舊 day-file 超過 7 天觸發 finding

- **WHEN** today=2026-05-11，`inbox/captured/heptabase/article/2026-05-03.md` 存在且為最舊
- **THEN** AuditReport 含 `kind=stale_heptabase_inbox`、`detail.oldest_date=2026-05-03`、`detail.days_behind=8`、`severity=warn` 的 Finding

#### Scenario: 最舊 day-file 在 7 天內不觸發 finding

- **WHEN** today=2026-05-11，inbox 內最舊 day-file 為 `2026-05-05.md`（6 天前）
- **THEN** AuditReport 不含 `stale_heptabase_inbox` Finding

#### Scenario: inbox 目錄不存在不報錯

- **WHEN** `inbox/captured/heptabase/` 目錄整個不存在（M1 ingest 從未跑過）
- **THEN** 檢查 graceful skip，不產 finding，audit() 不 raise exception

#### Scenario: inbox 內無 day-file 不報錯

- **WHEN** `inbox/captured/heptabase/<bucket>/` 目錄存在但僅含 `.gitkeep`，無 day-file
- **THEN** 檢查 graceful skip，不產 finding

#### Scenario: total_day_files 計入所有 bucket

- **WHEN** today=2026-05-11，github bucket 3 個 day-file、article bucket 5 個、youtube 2 個、threads 1 個，最舊 day-file 為 2026-05-01.md
- **THEN** Finding 的 `detail.total_day_files=11`、`detail.oldest_date=2026-05-01`、`detail.days_behind=10`

#### Scenario: 檢查不呼叫 LLM

- **WHEN** 在無 `ANTHROPIC_API_KEY` 的環境跑 audit()
- **THEN** `stale_heptabase_inbox` 檢查正常完成

