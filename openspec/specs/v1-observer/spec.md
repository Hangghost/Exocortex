## ADDED Requirements

### Requirement: opencode_client 模組可解析

`observe.py` SHALL 能正確 import `OpenCodeClient`，無需在 repo 外部手動設定 `PYTHONPATH`。實作方式為在 import 前將 `v0/` 目錄插入 `sys.path`。

#### Scenario: 直接執行 observe.py

- **WHEN** 執行 `python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe`，且 `v0/opencode_client.py` 存在
- **THEN** import 成功，不拋出 `ModuleNotFoundError`

#### Scenario: v0 目錄不存在時給出明確錯誤

- **WHEN** `v0/opencode_client.py` 不存在（例如 v0 目錄被意外移除）
- **THEN** 拋出 `ImportError` 並帶有可識別的錯誤訊息，不以靜默方式失敗

### Requirement: v1 observe 取代 v0 observer 的排程地位

系統 SHALL 以 `v1/observe.py` 作為每日唯一 observer 排程條目；`v0/observer.py` SHALL NOT 出現在 crontab 中。

#### Scenario: 正常排程執行

- **WHEN** crontab 在 20:00 觸發 v1 observe.py，且前一小時 capture.py 已完成
- **THEN** observe.py 讀取當日 high signals（若有），掃描 contexts/，產出 OBSERVATIONS.md entry

#### Scenario: capture 未執行時 observe 仍可獨立運行

- **WHEN** crontab 觸發 v1 observe.py，但當日 capture.py 未執行（`raw_signals/<date>/` 不存在）
- **THEN** observe.py 以純 v0 模式執行（無 high signals），正常產出 OBSERVATIONS.md entry，不 abort

### Requirement: 獨立 observe entry point

系統 SHALL 提供 `periodic_jobs/ai_heartbeat/src/v1/observe.py` 作為獨立執行的 observer entry point，基於 v0/observer.py 的 OpenCode Client 邏輯，額外將當日 `raw_signals/<date>/` 中 `triage="high"` 的 signals 納入觀察輸入。可單獨排程，與 capture.py 解耦。`observe.py` SHALL 能在不依賴外部 `PYTHONPATH` 設定的情況下正確 import `OpenCodeClient`。

#### Scenario: 正常執行（含 high signals）

- **WHEN** `python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe [YYYY-MM-DD]` 執行，且 `raw_signals/<date>/` 下存在 `triage="high"` 的 signals
- **THEN** 將 high signals 清單附加至 OpenCode prompt，讓 agent 同時掃描 contexts/ 檔案變動與 high signals，產出觀察條目並 append 至 `memory/OBSERVATIONS.md`

#### Scenario: 無 high signals 時正常執行

- **WHEN** observe.py 執行，但 `raw_signals/<date>/` 不存在或無 `triage="high"` 的 signals
- **THEN** 以純 v0 模式執行（只掃描 contexts/ 檔案變動），不因 signals 缺失而中止

#### Scenario: 冪等性保護

- **WHEN** 同一目標日期的 observe.py 被執行兩次
- **THEN** 第二次執行偵測到 OBSERVATIONS.md 已有當日 entry，直接跳過，不重複寫入
