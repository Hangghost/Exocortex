## ADDED Requirements

### Requirement: 多源原始信號捕獲

系統 SHALL 從 Calendar、Email 兩個來源自動捕獲原始信號，並以結構化 JSON 格式存入 `raw_signals/<YYYY-MM-DD>/` 目錄。每個信號 MUST 包含唯一 ID、來源類型、捕獲時間與內容摘要。`raw_signals/` 目錄 MUST 被 `.gitignore` 排除。

捕獲流程的 entry point SHALL 為 `periodic_jobs/ai_heartbeat/src/v1/capture.py`，不再透過 `main.py` 執行。

#### Scenario: Calendar 信號捕獲

- **WHEN** capture.py 執行，目標日期有 Calendar 事件
- **THEN** 捕獲每個事件的標題、開始時間、時長（不含參與者、地點等 PII 欄位），寫入 `raw_signals/<date>/calendar_<id>.json`，`source` 欄位為 `"calendar"`

#### Scenario: Email 信號捕獲

- **WHEN** capture.py 執行，目標日期有收到或發送的 Email
- **THEN** 捕獲每封 Email 的標題（subject）與寄件人，不捕獲 Email 正文，寫入 `raw_signals/<date>/email_<id>.json`，`source` 欄位為 `"email"`

#### Scenario: 來源不可用時的降級行為

- **WHEN** 某個來源（如 Calendar API）在捕獲時無法存取
- **THEN** 記錄來源不可用的警告，繼續處理其他可用來源，不中斷整個捕獲流程

---

### Requirement: 原始信號的結構化格式

每個原始信號 MUST 遵循以下 JSON schema，確保各 Stage 可一致讀取。

```json
{
  "id": "<uuid>",
  "source": "calendar|email",
  "captured_at": "<ISO8601>",
  "content": "<摘要文字>",
  "triage": null
}
```

`triage` 欄位初始值 SHALL 為 `null`，由 Stage 1 填入 `"high"` / `"uncertain"` / `"noise"`。

#### Scenario: 信號格式驗證

- **WHEN** 捕獲腳本寫入 raw_signals/
- **THEN** 每個 JSON 文件 MUST 包含 id、source、captured_at、content、triage 五個欄位，缺少任一欄位的信號 SHALL 被跳過並記錄錯誤

#### Scenario: 重複執行的冪等性

- **WHEN** 同一目標日期的捕獲腳本被執行兩次
- **THEN** 以相同 id 的信號不重複寫入（upsert 語意），確保冪等性
