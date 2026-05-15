# Spec: System State Coordination

## Purpose

定義跨角色、跨機器共享的執行狀態協調機制。透過兩層狀態檔案（git-tracked 的 `infra/state/system_state.json` 全域 high-water mark，以及 local-only 的 `raw_signals/<date>/<role>_run.json` 當日 audit log），讓 observer / reflector / state_audit / opsx:archive 等角色能彼此感知「上次成功跑到哪」、偵測 missed-run，並支援 producer-aware 命名決策（例如 archive 在 observer 已跑完當天時詢問 roll/stay）。
## Requirements
### Requirement: 兩層 state 檔案結構

系統 SHALL 維護兩層執行狀態紀錄：`infra/state/system_state.json`（git-tracked，全域 high-water mark cache）與 `raw_signals/<YYYY-MM-DD>/<role>_run.json`（本地當日 audit log，受 `.gitignore` 排除）。前者供 consumer 讀取「上次成功跑到哪」，後者供事後審計與 state_audit 偵測 missed-run 用。

#### Scenario: system_state.json 進 git

- **WHEN** 任一 role 完成執行並更新 state
- **THEN** `infra/state/system_state.json` 被寫入並可被 git 追蹤；不被 `.gitignore` 排除

#### Scenario: run log 不進 git

- **WHEN** 任一 role 寫入 `raw_signals/<date>/<role>_run.json`
- **THEN** 該檔案位於既有的 `raw_signals/` 目錄下，受既有 `.gitignore` 規則排除，不進入 git history

### Requirement: system_state.json schema

`infra/state/system_state.json` MUST 為 UTF-8 JSON 物件，含 `version: int` 與 `roles: object` 兩個 top-level 欄位。`roles` 物件的 key SHALL 為角色名稱字串，value 為含以下欄位的物件：`last_started_at`（ISO 8601 timestamp with timezone）、`last_finished_at`（ISO 8601 timestamp with timezone 或 null 若 status=running）、`last_target_date`（YYYY-MM-DD 字串）、`last_status`（`"ok"` / `"failed"` / `"running"` 之一）。其他欄位可選。

#### Scenario: 標準 state 結構

- **WHEN** observer 執行成功後寫 state
- **THEN** `system_state.json` 含 `{"version": 1, "roles": {"observer": {"last_started_at": "<ISO>", "last_finished_at": "<ISO>", "last_target_date": "YYYY-MM-DD", "last_status": "ok"}, ...}}`

#### Scenario: 角色執行中

- **WHEN** observer 進入點剛寫入 state 但主流程未完成
- **THEN** state 中 observer 區段的 `last_status` 為 `"running"`，`last_finished_at` 為 null

### Requirement: run log schema

`raw_signals/<date>/<role>_run.json` MUST 為 UTF-8 JSON 物件，含以下欄位：`kind`（字串 `<role>_run`）、`role`（角色名稱）、`started_at`（ISO 8601 timestamp）、`finished_at`（ISO 8601 timestamp 或 null）、`target_date`（YYYY-MM-DD）、`status`（同 system_state 的 last_status）。observer / reflector 額外含 `session_id`。失敗時可加 `error_summary` 欄位記錄例外摘要。

#### Scenario: 寫入完整 run log

- **WHEN** observer 完成執行
- **THEN** `raw_signals/<target_date>/observer_run.json` 被寫入，含 kind/role/started_at/finished_at/target_date/status/session_id 欄位

#### Scenario: 失敗時仍寫 run log

- **WHEN** observer 主流程拋出例外
- **THEN** `raw_signals/<target_date>/observer_run.json` 仍被寫入，status=failed，含 error_summary 欄位

### Requirement: Atomic write

寫入 `infra/state/system_state.json` 與 `raw_signals/<date>/<role>_run.json` SHALL 採用「先寫 `.tmp` 後 `os.replace`」的 atomic 模式，保證進程中斷時檔案不會處於 partial 狀態。

#### Scenario: 寫入過程被中斷

- **WHEN** 寫入 system_state.json 過程中進程被 SIGKILL
- **THEN** `system_state.json` 要嘛保持原內容、要嘛已是新的完整內容；不會出現損壞的 JSON

### Requirement: 寫入時機

每個 role 在執行流程中 SHALL 依以下順序寫 state：

1. 進入主流程前：寫 `last_status: "running"` 與 `last_started_at`
2. 主流程成功完成：寫 `last_status: "ok"` 與 `last_finished_at`，並寫 run log
3. 主流程例外：寫 `last_status: "failed"` 與 `last_finished_at`，並寫含 error_summary 的 run log

#### Scenario: 角色執行流程的 state 演進

- **WHEN** observer 從進入到完成成功
- **THEN** state 經歷 `running` → `ok` 兩階段，run log 在 ok 階段寫入

#### Scenario: 角色失敗仍留下記錄

- **WHEN** observer 在執行中途拋出例外
- **THEN** state 從 `running` 變為 `failed`，run log 寫入但 status=failed

### Requirement: Consumer fallback 行為

所有讀取 `system_state.json` 的 consumer SHALL 在以下情境降級至原啟發式策略：檔案不存在（首次部署）、JSON parse 失敗、缺少預期 role / 欄位。降級時 SHALL 記錄一條 🟢 Low 觀察條目（透過既有觀察管道，如 OBSERVATIONS.md 或 log 訊息）提示 state 缺失。

#### Scenario: state 檔案不存在時降級執行

- **WHEN** observer 啟動時 `infra/state/system_state.json` 不存在
- **THEN** observer 仍以原冪等性檢查邏輯（grep OBSERVATIONS.md）執行，不 abort，並 log 一條提示

#### Scenario: state 檔案 schema 損壞時降級

- **WHEN** opsx:archive 讀 state 但 JSON parse 失敗
- **THEN** archive 流程 fallback 至「正常使用 today 命名」，不 abort

#### Scenario: 預期 role 缺席時降級

- **WHEN** observer 讀 state 但 `roles.observer` 欄位不存在（首次寫入前）
- **THEN** observer 視為「從未跑過」，繼續執行；不 abort

### Requirement: Producer-aware 命名（opsx:archive）

`opsx:archive` 在執行歸檔目錄移動前 SHALL 讀 `infra/state/system_state.json`。若 `roles.observer.last_target_date` 等於 today 且 `last_status` 為 `ok`，SHALL 透過 AskUserQuestion 詢問使用者選擇：

- **A. Roll**：使用 tomorrow 日期前綴命名歸檔目錄（明天 observer 會看到，建議選項）
- **B. Stay**：使用 today 日期前綴命名，並在歸檔目錄根放置 `_late.json` metadata 標記（內含 `archived_at` 時間戳與 observer `last_finished_at`），同時提示使用者建議手動補一條到 OBSERVATIONS.md

#### Scenario: observer 已跑完當天

- **WHEN** opsx:archive 執行時 system_state 顯示 observer last_target_date=today, last_status=ok
- **THEN** 觸發 AskUserQuestion 提供 roll / stay 選項

#### Scenario: observer 未跑當天

- **WHEN** opsx:archive 執行時 system_state 顯示 observer last_target_date != today 或 last_status != ok
- **THEN** 直接使用 today 命名，不觸發詢問（既有行為）

#### Scenario: state 檔案不存在

- **WHEN** opsx:archive 執行時 `infra/state/system_state.json` 不存在
- **THEN** 直接使用 today 命名 + 提示「state 缺失，使用降級命名」

#### Scenario: 使用者選擇 stay 時寫 metadata.late

- **WHEN** AskUserQuestion 中使用者選擇「Stay」
- **THEN** archive 目錄根產生 `_late.json` 檔案，含 `archived_at` 與 `observer_last_finished_at`，並回傳訊息提示「observer 不會自動看到，建議手動補 OBSERVATIONS」

### Requirement: 跨機器共享 state

`infra/state/system_state.json` SHALL 進入 git 追蹤，使多台機器（MacBook Pro / Mac mini）能讀到同一份 state。`raw_signals/<date>/<role>_run.json` SHALL 維持 local-only（不進 git），各機器各自記錄當日 audit log。

#### Scenario: 一台機器跑 observer，另一台機器讀 state

- **WHEN** MacBook Pro 跑 observer 完成、commit 並 push system_state；Mac mini 隨後 pull
- **THEN** Mac mini 上 opsx:archive 讀到的 state 與 MacBook Pro 上的 state 一致

#### Scenario: 兩台機器同日 run log 不互通

- **WHEN** 兩台機器各自跑了某 role
- **THEN** 各自的 `raw_signals/<date>/<role>_run.json` 留在本機，不進 git；system_state 反映最後寫入的那台機器的狀態

### Requirement: state 檔案的版本欄位

`system_state.json` 與 run log 物件 SHOULD 含 `version: int` 欄位（system_state.json 為必填 top-level 欄位）。Consumer 讀取時 SHALL 檢查版本相容性；遇到未知版本 SHALL fallback 至原啟發式策略並記錄 🟢 觀察。

#### Scenario: 已知版本

- **WHEN** consumer 讀 state，version=1
- **THEN** 正常解析欄位

#### Scenario: 未知版本

- **WHEN** consumer 讀 state，version=99
- **THEN** consumer fallback 並記錄提示，不 abort

### Requirement: Role run 必須收斂到 terminal state

每個 periodic role 的 `main()` SHALL 確保：在 `last_status` 被設為 `running` 之後，program 結束時 `last_status` MUST 為 terminal state（`ok` 或 `failed`），且 `last_finished_at` MUST 不為 null。允許的程式結束路徑包含：正常 return、Python exception、`sys.exit()`、SIGTERM 訊號；唯有 SIGKILL 與 process 被 OS 強制終止屬不可控例外。

實作 SHALL 透過 try/finally、`atexit` handler、或 SIGTERM signal handler 等機制，確保 `update_role_state` 與 `write_run_log` 在所有可控結束路徑都被呼叫一次（不允許重複寫，但 best-effort 寫一次必須成立）。

#### Scenario: Role 正常完成

- **WHEN** role main() 走完成功路徑（`_run` 無例外、無外部訊號）
- **THEN** `system_state.json` 對應 role 區段 `last_status="ok"`、`last_finished_at` 為實際完成時間；`raw_signals/<date>/<role>_run.json` 同步寫入 `status="ok"`

#### Scenario: Role 拋 Python exception

- **WHEN** role main() 中 `_run` 拋出例外
- **THEN** `system_state.json` 對應 role 區段 `last_status="failed"`、`last_finished_at` 為例外時間；`raw_signals/<date>/<role>_run.json` 同步寫入 `status="failed"` 且含 `error_summary`

#### Scenario: Role 收到 SIGTERM

- **WHEN** role main() 在 `running` 期間收到 SIGTERM 訊號
- **THEN** signal handler SHALL 將其轉為 SystemExit，atexit handler 寫入 `last_status="failed"`、`last_finished_at` 為終止時間；不允許留下 `last_status="running"` 的孤兒狀態

#### Scenario: Role 收到 SIGKILL

- **WHEN** role main() 在 `running` 期間收到 SIGKILL 訊號（process 強制終止，無法執行任何 handler）
- **THEN** `system_state.json` 可能停留在 `last_status="running"`；此情境屬不可控例外，由 state_audit 的 `stale_running_role` finding 在 ≤ threshold 小時內偵測補位（見 state-audit spec）

