# state_audit

純規則性的「儲存庫狀態審計」角色。與 `ai_heartbeat/` 平行存在，但**無
LLM、無 OpenCode、無 Anthropic API 依賴**——只用 Python 標準庫 + `git` CLI。

## 角色定位

回答一個固定問題：「現在這個 repo 處於 observer 友善的狀態嗎？」
若不友善，輸出可被人類讀、也可被 observer 讀的 `AuditReport`。

五項檢查：

1. `dirty_working_tree` — `git status --porcelain` 非空
2. `unmerged_content_branch` — 本地 `content/YYYY-MM-DD` 未進 main
3. `stale_active_project_bridge` — `projects/<name>/PROJECT.md` 比最新
   `*<name>_(update|retrospective).md` 新（git mtime 比較，跨機 clone 一致）
4. `unpushed_branch` — 本地分支與 upstream 不一致（含 no_upstream / ahead /
   diverged）
5. `main_behind_origin` — `origin/main` 領先 local main

## 與 ai_heartbeat 的職責分界

| | `state_audit/` | `ai_heartbeat/` |
|---|---|---|
| 依賴 | 標準庫 + git CLI | OpenCode + Anthropic API |
| 角色 | 規則檢查 | 觀察、反思、產出語意條目 |
| 輸出 | `AuditReport` (json) + inbox 摘要 | `OBSERVATIONS.md` 條目 |
| Mutation | 無（cron 僅寫檔） | 無（observer 寫 OBSERVATIONS.md） |

state_audit 不寫 `OBSERVATIONS.md`、不修 `rules/`、不切分支、不 commit、不 push。

## 輸出契約

- `inbox/captured/<YYYY-MM-DD>_state_audit.md`：人類可讀摘要，**僅在 findings 非空時寫入**
- `raw_signals/<YYYY-MM-DD>/state_audit.json`：機器可讀（observer 讀），**永遠寫入**
  （即使 findings 為空，提供「audit 已跑」的 meta）

兩者皆使用 atomic write（先 `.tmp` 後 `os.replace`）。

## 進入點

- `core.audit()`：lib，給 `/ctx:eod` 與 `cron.py` 共用
- `cron.py`：18:30 silent backstop，呼叫 `git fetch --all` 後 `audit()` 並寫檔

```bash
# 手動跑（dev / debug）
python -m infra.periodic_jobs.state_audit.cron
```

## 為什麼不內嵌進 ai_heartbeat

- 依賴隔離：state_audit 不該被 LLM API 失效拖累
- 演進節奏不同：規則檢查穩定；observer prompt 高頻迭代
- import 路徑乾淨：`/ctx:eod` 只 import 規則邏輯，不拉 OpenCode client

詳見 `openspec/changes/add-state-audit/design.md` 的 D1。
