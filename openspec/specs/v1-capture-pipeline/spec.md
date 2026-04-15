## ADDED Requirements

### Requirement: 獨立 capture entry point

系統 SHALL 提供 `periodic_jobs/ai_heartbeat/src/v1/capture.py` 作為獨立執行的 entry point，執行 L0 capture + triage pipeline（Steps 1-3, 5-6），不包含觀察步驟。可單獨排程，與 observe.py 解耦。

#### Scenario: 正常執行

- **WHEN** `python -m periodic_jobs.ai_heartbeat.src.v1.capture [YYYY-MM-DD]` 執行
- **THEN** 依序執行 capturer → stage1 triage → stage2 judgment → archive → gc，完成後 `raw_signals/<date>/` 下所有 signal 的 `triage` 欄位均為 `"high"` 或 `"noise"`，noise signals 已移入 archive

#### Scenario: capture 失敗時中止

- **WHEN** L0 capturer（Step 1）執行失敗
- **THEN** pipeline 中止，不繼續執行 triage steps，記錄錯誤並以非零 exit code 結束

#### Scenario: triage 失敗時繼續

- **WHEN** Stage 1 或 Stage 2 執行失敗
- **THEN** 記錄錯誤，繼續執行後續步驟（archive/gc），不中止整個 pipeline
