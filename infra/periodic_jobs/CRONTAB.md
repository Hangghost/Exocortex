# Crontab 配置指南

本文件描述 context infrastructure 系統所需的定時任務。

---

## 時間線總覽

```
19:00   → AI Heartbeat v1 Capture: L0 捕獲 → 三級分流 → archive → GC（輸出 raw_signals/<date>/）
20:00   → AI Heartbeat v1 Observer: 讀取 high signals + 掃描 contexts/，寫入 OBSERVATIONS.md
          （依賴 capture 先執行；capture 未執行時 high signals 為空，不影響 observer 正常執行）
Weekly 週日 21:00  → AI Heartbeat Reflector: 合併/提升/清理記憶
```

---

## 核心任務說明

### AI Heartbeat v1 Capture（每日）

L0 訊號捕獲 + 兩階段 triage + archive/GC。輸出落地於 `raw_signals/<date>/`，供 v1 Observer 讀取。

- **指令碼**：`periodic_jobs/ai_heartbeat/src/v1/capture.py`
- **依賴**：`ANTHROPIC_API_KEY`、Google OAuth tokens（`GOOGLE_CREDENTIALS`、`GOOGLE_CAL_TOKEN`、`GOOGLE_GMAIL_TOKEN`）
- **建議時間**：每日 19:00
- **錯誤策略**：capture 失敗 → abort（非零 exit code）；triage/archive 失敗 → continue

### AI Heartbeat v1 Observer（每日）

基於 OpenCode Client 的 agentic observer，額外將 capture 產出的 `triage="high"` signals 納入觀察輸入。

- **指令碼**：`periodic_jobs/ai_heartbeat/src/v1/observe.py`
- **依賴**：OpenCode Server API（`OPENCODE_API_URL`）；需在 capture 之後執行
- **建議時間**：每日 20:00
- **冪等性**：OBSERVATIONS.md 已有當日 entry 時自動跳過
- **依賴順序**：capture.py → observe.py；若 capture 未執行，high signals 為空，observer 仍正常掃描 contexts/

### AI Heartbeat Reflector（每週）

合併、提升、清理 OBSERVATIONS.md 中積累的觀察，蒸餾為更高層次的認知。

- **指令碼**：`periodic_jobs/ai_heartbeat/src/v0/reflector.py`
- **依賴**：OpenCode Server API（`OPENCODE_API_URL`）
- **建議時間**：每週日 21:00

### Crontab Monitor（每日）

自主審計所有 crontab 任務的健康狀態，發現異常時傳送告警郵件。


### AI News Survey（每日/每週）

呼叫 AI Agent 生成 AI 行業日報或週報，可釋出到 Kit 訂閱者或傳送個人郵件。


---

## 示例 crontab 配置

將以下內容新增到 `crontab -e`。**使用前請將 `/path/to/your/workspace` 替換為實際路徑。**

```cron
# ── 時區說明 ──────────────────────────────────────────────
# 以下時間均為本地時間。如需指定時區，在 crontab 頂部新增：
# TZ=America/Los_Angeles

# AI Heartbeat v1 Capture — 每日 19:00（L0 捕獲 + triage + archive/GC）
# 依賴：.env 中需設定 ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS, GOOGLE_CAL_TOKEN, GOOGLE_GMAIL_TOKEN
# 首次執行需在互動環境中完成 Google OAuth 授權（產生 token.json）
0 19 * * * cd /path/to/your/workspace && /path/to/your/workspace/.venv/bin/python -m periodic_jobs.ai_heartbeat.src.v1.capture >> /tmp/capture_v1.log 2>&1

# AI Heartbeat v1 Observer — 每日 20:00（OpenCode agentic observer，需 capture 先完成）
# 依賴：OpenCode Server 必須運行（OPENCODE_API_URL）
0 20 * * * cd /path/to/your/workspace && /path/to/your/workspace/.venv/bin/python -m periodic_jobs.ai_heartbeat.src.v1.observe >> /tmp/observe_v1.log 2>&1

# AI Heartbeat Reflector — 每週日 21:00
0 21 * * 0 cd /path/to/your/workspace && /path/to/your/workspace/.venv/bin/python periodic_jobs/ai_heartbeat/src/v0/reflector.py >> /tmp/reflector.log 2>&1

```

---

## 注意事項

1. **路徑替換**：所有 `/path/to/your/workspace` 必須替換為你的實際絕對路徑。
2. **虛擬環境**：指令碼依賴 `.venv` 中的 Python 包，確保先執行 `uv pip install -r requirements.txt`（如有）。
3. **環境變數**：cron 環境不會自動載入 `.env`，建議在指令碼中顯式載入，或在 crontab 中用 `env $(cat .env | xargs)` 注入。
4. **時區**：macOS cron 預設使用系統時區；Linux 伺服器建議在 crontab 頂部顯式設定 `TZ=`。
5. **日誌**：示例中日誌寫入 `/tmp/`，生產環境建議改為持久化路徑（如 `logs/` 目錄）。
6. **依賴順序**：v1 Capture（19:00）→ v1 Observer（20:00）→ Reflector（週日 21:00）。v1 Observer 需在 capture 完成後執行。
