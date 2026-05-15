# cc-hooks-capture Specification

## Purpose
TBD - created by archiving change add-cc-hooks-capture. Update Purpose after archive.
## Requirements
### Requirement: CC hooks 作為 L0 事件源頭

系統 SHALL 利用 Claude Code 原生 hook 介面（`SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / PostToolUseFailure / Stop / SessionEnd / SubagentStart / SubagentStop`）作為對話 L0 capture 的事件源頭。Hook 觸發時 SHALL 寫事件到 `inbox/captured/cc_events/<session_id>/` 目錄下對應檔案。Hook 層 SHALL NOT 執行任何網路 I/O、LLM 呼叫、git 操作；僅做 metadata 收集 + 檔案寫入。

session 級不變欄位（cwd / transcript_path / model / source）由 SessionStart hook 寫入單檔 `session.json`；事件級欄位（prompt 文字、tool 執行結果等）由各事件 hook 寫入獨立檔。

#### Scenario: P0 Hook — SessionStart

- **WHEN** session 啟動 / resume / clear / compact 觸發 `SessionStart` hook
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/session.json`（單檔，覆寫式），含 session_id / cwd / transcript_path / source / model / started_at 六欄

#### Scenario: P0 Hook — UserPromptSubmit

- **WHEN** 使用者送出 prompt 觸發 `UserPromptSubmit` hook
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/prompt_<ts>_<uuid>.json`，內容含 `event_type=prompt`、`captured_at`、`prompt_text` 三個欄位（不再含 session_id / cwd / transcript_path）

#### Scenario: P0 Hook — SessionEnd

- **WHEN** session 結束觸發 `SessionEnd` hook
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/_session_done.json`，內容含 `event_type=session_done`、`captured_at`、`reason`、`prompt_count`、`duration_seconds` 五欄（不再含 transcript_path / session_id / cwd）

#### Scenario: P1 Hook — PostToolUseFailure Bash 錯誤

- **WHEN** `PostToolUseFailure` hook 觸發且 `tool_name=Bash`
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/tool_error_<ts>_<uuid>.json`，內容含 `event_type=tool_error`、`captured_at`、`tool_name`、`command`、`stderr_excerpt`、`stdout_excerpt`、`interpretation`、`interrupted` 八欄（不再含 session_id / cwd / transcript_path）

#### Scenario: P1 Hook — Subagent 生命週期

- **WHEN** Claude 啟動或完成 subagent 觸發 `SubagentStart` 或 `SubagentStop` hook
- **THEN** 系統寫入對應的 `subagent_start_*.json` 或 `subagent_done_*.json`（schema 詳見「Subagent 生命週期 hooks」requirement）

#### Scenario: 不在範圍的 hook 不被觸發

- **WHEN** 系統執行 `Stop`、`PreToolUse`、`PostToolUse(Read)`、`PostToolUse(Edit)`、`PostToolUse(Write)`、`PreCompact`、`PostCompact` 等本 capability 範圍外的 hook
- **THEN** 不產生任何 `inbox/captured/cc_events/` 檔案（`PostToolUse(Edit|Write)` 為前一版的 arch_change 來源，已 deprecated；其餘為 P2 或 out-of-scope）

---

### Requirement: Session header 寫入機制

`SessionStart` hook 觸發時，系統 SHALL 寫入單檔 session header 到 `inbox/captured/cc_events/<session_id>/session.json`，含 session 級不變的 metadata，避免後續每筆事件重複抄錄。Header 的存在解耦了「session 級事實」與「事件級事實」兩種資料的生命週期。

Resume / clear / compact 觸發 SessionStart 時 SHALL 覆寫 session.json（單檔語意），並透過 `source` 欄位區分本次觸發類型，下游 bridge 取最新的 header 狀態。

#### Scenario: SessionStart 寫入 session.json

- **WHEN** 使用者啟動新 CC session 觸發 `SessionStart` hook（source=startup）
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/session.json`，內容含 `session_id`、`cwd`、`transcript_path`、`source`（startup|resume|clear|compact）、`model`、`started_at` 六個欄位

#### Scenario: Resume 覆寫既有 session.json

- **WHEN** 使用者 resume 既有 session 觸發 `SessionStart`（source=resume）
- **THEN** 系統覆寫該 session_id 目錄下的 `session.json`，新檔的 `source` 欄位為 `resume`，`started_at` 為本次 resume 觸發時間

#### Scenario: Header 缺漏時 bridge 容錯

- **WHEN** bridge 處理某 session 目錄但找不到 `session.json`（hook 失敗或 session 在 SessionStart 前就被觀察）
- **THEN** bridge SHALL 仍處理該 session 的 events，header 欄位以 `null` / 空字串標記；SHALL NOT 因 header 缺漏整批 events 都跳過

---

### Requirement: Subagent 生命週期 hooks

系統 SHALL 利用 `SubagentStart` / `SubagentStop` hook 捕獲 subagent 生命週期事件，作為「subagent 委派觀察」訊號來源。原 design 將 PostToolUse(Task) 列為 P2 follow-up；本次優化改採官方提供的專屬 lifecycle 事件，payload 更乾淨、語意明確。

> 實作 probe（task 3.1–3.2）確認 CC 實際 fire 的是 `SubagentStart` / `SubagentStop` 而非 docs 描述的 `TaskCreated` / `TaskCompleted`。Payload 欄位以實測為準：使用 `agent_id`（而非 `task_id`）、`agent_type`（而非 `subagent_type`），`description` 不在 payload 內（屬 PreToolUse(Task) 的 tool_input，本 capability 不另外捕獲），`SubagentStop` 提供 `last_assistant_message` 作為結果摘要。

#### Scenario: SubagentStart 寫入 subagent_start

- **WHEN** Claude 透過 Agent tool 啟動 subagent 觸發 `SubagentStart` hook
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/subagent_start_<ts>_<uuid>.json`，內容含 `event_type=subagent_start`、`captured_at`、`agent_id`、`agent_type`

#### Scenario: SubagentStop 寫入 subagent_done

- **WHEN** subagent 完成觸發 `SubagentStop` hook
- **THEN** 系統寫入 `inbox/captured/cc_events/<session_id>/subagent_done_<ts>_<uuid>.json`，內容含 `event_type=subagent_done`、`captured_at`、`agent_id`、`agent_type`、`last_assistant_message`、`agent_transcript_path`、`stop_hook_active`

#### Scenario: Subagent 事件不重抄 session 級欄位

- **WHEN** 檢查 `subagent_start_*.json` 或 `subagent_done_*.json`
- **THEN** 該事件 SHALL NOT 含 `session_id`、`cwd`、`transcript_path` 三欄（這些已在同目錄的 `session.json` 中）

---

### Requirement: Hook 內無過濾原則（origin filter 例外）

Hook script SHALL NOT 在 hook 端對事件內容做**語意/價值過濾**（prompt 長度判斷、關鍵詞匹配、訊號類別判斷）。所有事件 SHALL 全寫，過濾與分類交給下游 bridge / triage / observer。

**例外**：UserPromptSubmit hook SHALL 過濾掉 CC 注入的**系統訊息事件**（task-notification / system notification）——這些不是使用者意圖、亦非 hook 該捕獲的訊號來源。判斷方式為 prompt 開頭 500 字內的精確 marker 字串匹配（mechanical origin filter，非語意判斷），目前 marker 為：

- `[SYSTEM NOTIFICATION - NOT USER INPUT]`
- `<task-notification>`

這個例外不違反「無價值過濾」原則——它是區分**事件來源**（user vs system-injected），不是判斷**事件價值**。

#### Scenario: 短 prompt 仍被捕獲

- **WHEN** 使用者輸入短 prompt（如「不對」、「ok」）
- **THEN** 該 prompt 仍被 `UserPromptSubmit` hook 寫入 cc_events，hook script SHALL NOT 因為長度短而跳過

#### Scenario: Hook 端不做關鍵詞匹配

- **WHEN** 使用者 prompt 含負向語彙（如「錯了」、「上次也…」）
- **THEN** hook script SHALL NOT 因關鍵詞做特殊標記或寫入不同檔；該 prompt 與其他 prompt 走同一個 prompt event 路徑，標記由 bridge 或 reflector 在下游做

#### Scenario: 系統注入的 task-notification 被過濾

- **WHEN** CC 透過 `UserPromptSubmit` hook 傳入 prompt，prompt 開頭 500 字內含 `<task-notification>` 或 `[SYSTEM NOTIFICATION - NOT USER INPUT]` marker
- **THEN** hook SHALL NOT 寫事件檔；inbox 不出現對應 prompt_*.json

#### Scenario: 使用者引用 marker 不被誤過濾

- **WHEN** 使用者 prompt 在後段（500 字之後）出現 `<task-notification>` 字串（例如貼出 log 討論）
- **THEN** hook SHALL 仍寫事件檔（避免 false positive 漏抓使用者意圖）

---

### Requirement: Hook 用 Python stdlib 實作

Hook scripts SHALL 放置於 `.claude/hooks/`，shebang 為 `#!/usr/bin/env python3`，僅使用 Python 標準庫（json / pathlib / datetime / uuid / sys / os），不依賴 uv 環境或外部套件。共用邏輯 SHALL 抽至 `.claude/hooks/lib/event_writer.py`。

#### Scenario: Hook script 可獨立執行

- **WHEN** 從命令列直接執行 hook script 並透過 stdin 餵入 hook payload JSON
- **THEN** script 正常完成，於 `inbox/captured/cc_events/` 寫入對應事件檔，不需要啟動 uv venv 或安裝套件

#### Scenario: Hook 失敗不阻塞 user input

- **WHEN** hook script 執行時遇到例外（如 disk full、permission denied）
- **THEN** script 以 try/except 捕獲，寫 fallback log 到 `~/.claude/logs/hooks_failed/<date>.log`，且 exit code 為 0（不傳遞錯誤給 CC，避免阻塞 user input）

---

### Requirement: Hook config 為 project-scoped

Hook 註冊 SHALL 寫於 repo 內 `.claude/settings.json`（git tracked）；SHALL NOT 寫於 `~/.claude/settings.json`（user-scoped）。Hook script 路徑 SHALL 使用 `$CLAUDE_PROJECT_DIR/.claude/hooks/<script>` 形式的 portable 絕對路徑前綴（不含硬編碼的 `/Users/<name>/` 等機器特定 root），確保跨機 deploy 與 cross-worktree 執行一致。詳細約束見 requirement「Hook command 必須使用 $CLAUDE_PROJECT_DIR 絕對路徑」。

#### Scenario: 跨機 hook 同步

- **WHEN** 使用者在 MacBook Pro 修改 `.claude/settings.json` 的 hook config 並 push
- **THEN** Mac mini `git pull` 後 hook config 自動生效，無需手動配置

#### Scenario: Hook script 路徑為 portable 絕對路徑

- **WHEN** 檢視 `.claude/settings.json` 的 hook 註冊
- **THEN** 每個 hook command 以 `$CLAUDE_PROJECT_DIR/` 為前綴（不含 `/Users/<name>/` 等硬編碼絕對路徑），確保兩台機器以及任何 worktree session 都執行主 repo 的同一份 script

---

### Requirement: Hook 寫入 idempotency

Hook 層 SHALL 為 stateless write-only：每個事件寫獨立檔，檔名以 `<event_type>_<ISO8601_compact_ts>_<short_uuid>.json` 形式確保不撞名。Hook SHALL NOT 讀取既有 inbox 檔案做去重檢查。去重責任屬於下游 bridge capturer。

#### Scenario: 連續事件不撞名

- **WHEN** 使用者快速送出兩個 prompt（同一 ts 秒內）
- **THEN** 兩個 prompt 事件分別寫入兩個不同檔（透過 uuid 後綴區分），不發生覆寫

#### Scenario: Hook 無讀取行為

- **WHEN** hook 被觸發
- **THEN** hook script 只執行檔案寫入操作，SHALL NOT 讀取 `inbox/captured/cc_events/` 既有檔案內容

---

### Requirement: 事件目錄受 .gitignore 排除

`inbox/captured/cc_events/` SHALL 被 `.gitignore` 規則排除（與 `raw_signals/` 同樣處理）。`inbox/captured/cc_events/` 下 SHALL 僅保留 `.gitkeep` 與 `README.md` 進入 git，避免敏感對話內容意外上傳。

#### Scenario: 事件檔不會被 git track

- **WHEN** hook 寫入新事件檔，使用者執行 `git status`
- **THEN** 該事件檔 NOT 出現在 untracked / modified 清單

#### Scenario: README 與 gitkeep 仍受 git 管理

- **WHEN** repo 初始化或 clone 後
- **THEN** `inbox/captured/cc_events/.gitkeep` 與 `README.md` 存在於 git tracked 檔案中

---

### Requirement: cc_events 事件 JSON schema

每個 cc_events 事件檔 MUST 為合法 JSON object。系統採用「session header + event delta」兩層 schema：

**Session header**（`session.json`，由 SessionStart 寫入單檔）必含欄位：

```json
{
  "session_id": "<CC session uuid>",
  "cwd": "<absolute path at session start>",
  "transcript_path": "<absolute path to jsonl>",
  "source": "startup|resume|clear|compact",
  "model": "<model id at session start>",
  "started_at": "<ISO8601>"
}
```

**Event delta**（每個事件檔）必含欄位：

```json
{
  "event_type": "prompt|session_done|tool_error|subagent_start|subagent_done",
  "captured_at": "<ISO8601>",
  "...event-specific fields..."
}
```

事件檔 SHALL NOT 含 `session_id`、`cwd`、`transcript_path` 三欄——這些屬 session 級資料，由 bridge 從同目錄 `session.json` 讀取後 join 進 raw_signals。事件特有欄位 SHALL 依 event_type 而異（如 `prompt_text` for prompt、`command/stderr_excerpt` for tool_error、`task_id` for subagent_*）。

#### Scenario: Session header schema 驗證

- **WHEN** 檢查任一 `session.json`
- **THEN** 含 `session_id`、`cwd`、`transcript_path`、`source`、`model`、`started_at` 六個欄位

#### Scenario: Event delta schema 驗證

- **WHEN** 檢查任一事件檔（prompt / tool_error / session_done / subagent_*）
- **THEN** 含 `event_type` 與 `captured_at` 兩個基本欄位，且 SHALL NOT 含 `session_id`、`cwd`、`transcript_path` 三個 session 級欄位

#### Scenario: prompt 事件特有欄位

- **WHEN** 檢查 `prompt_*.json`
- **THEN** 額外含 `prompt_text` 欄位（完整 prompt 文字，非截斷）

#### Scenario: tool_error 事件特有欄位

- **WHEN** 檢查 `tool_error_*.json`
- **THEN** 額外含 `tool_name`、`command`、`description`、`stderr_excerpt`、`stdout_excerpt`、`interpretation`、`interrupted` 欄位

#### Scenario: Bridge join header 進 raw_signals

- **WHEN** bridge 處理某事件檔產生 raw_signal
- **THEN** raw_signal 中 SHALL 含 session 級欄位（cwd / transcript_path / source / model）——這些由 bridge 從同目錄 `session.json` 讀出後 fold 進 raw_signal payload，符合既有 raw_signals JSON schema

### Requirement: Hook 路徑解析 worktree-aware

`event_writer.py` SHALL 將 CC hook 事件寫入 **main repository 的** `inbox/captured/cc_events/<session_id>/`，不論該 hook 是從 main repo 還是任一 git worktree 觸發。`REPO_ROOT` 解析 SHALL 識別 `.git` 為 file（worktree 標記）的情境，parse 其 `gitdir:` 行內容，回推 main repo 根目錄。

實作 SHALL 為純 Python（不呼叫 `git` binary、不使用 subprocess），確保 hook 啟動延遲不增加可感知量。解析失敗時 SHALL fallback 到 legacy `Path(__file__).resolve().parents[3]` 行為，以維持 hook layer「絕不阻塞使用者輸入」的 contract。

設計依據：`.claude/hooks/` 為 git-tracked，每個 worktree 含獨立 hook script copy；單純使用 `Path(__file__).parents[3]` 會把事件寫到 worktree-local inbox，導致 session 事件分散於多個 inbox，bridge / observer / reflector 無法觀察到完整 session 軌跡。

#### Scenario: 從 main repo 觸發 hook

- **WHEN** Claude Code session cwd 在 main repo 根目錄或子目錄，hook 被觸發
- **THEN** event 檔 SHALL 寫入 `<main-repo>/inbox/captured/cc_events/<session_id>/`

#### Scenario: 從 project worktree 觸發 hook

- **WHEN** Claude Code session cwd 在 `<main-repo>/.claude/worktrees/<name>/` 或其子目錄，hook 被觸發
- **THEN** event 檔 SHALL 寫入 `<main-repo>/inbox/captured/cc_events/<session_id>/`，**而非** `<main-repo>/.claude/worktrees/<name>/inbox/captured/cc_events/<session_id>/`

#### Scenario: 同一 session 跨越 EnterWorktree / ExitWorktree 仍寫入單一 inbox

- **WHEN** session 開始時 cwd 在 main，中途 EnterWorktree 進入 `<main-repo>/.claude/worktrees/<name>/`，後續又 ExitWorktree 回 main
- **THEN** session 全程所有 hook 事件 SHALL 累積於 `<main-repo>/inbox/captured/cc_events/<session_id>/` 單一目錄，無事件落到 worktree 內 inbox

#### Scenario: 解析失敗 fallback

- **WHEN** `_resolve_main_repo_root()` 拋出 `ValueError` 或 `OSError`（例如 `.git` 檔格式異常、檔案無法讀取）
- **THEN** `REPO_ROOT` SHALL 退回 `Path(__file__).resolve().parents[3]`，hook 仍能寫入事件檔（即使位置可能不正確），不 raise 阻塞使用者

### Requirement: Hook command 必須使用 $CLAUDE_PROJECT_DIR 絕對路徑

`.claude/settings.json` 內所有 hook command 字串 SHALL 以 `$CLAUDE_PROJECT_DIR/` 為前綴，引用 `.claude/hooks/` 下的腳本。SHALL NOT 使用相對路徑（例如 `.claude/hooks/<script>.py`）或硬編碼絕對路徑（例如 `/Users/.../.claude/hooks/<script>.py`）。

理由：Claude Code 在執行 hook command 時以 session cwd 為基準解析相對路徑。當 session 跑在 `.claude/worktrees/<name>/` 下且該 worktree 的 branch 沒有 check in `.claude/hooks/` 檔案時（包含但不限於 long-lived `project/*` branch），相對路徑會解析失敗，6 個 capture hook 全部 missing，capture pipeline 對該 worktree 完全失能。`$CLAUDE_PROJECT_DIR` 是 Claude Code 注入到 hook context 的 env var，永遠指向主 repo root，不受 worktree 影響。此規則與內部 `event_writer` 從 worktree 解析回主 repo root 的邏輯（commit `69a5f8f`）形成內外對稱。

#### Scenario: settings.json 內 hook command 用絕對路徑前綴

- **WHEN** 開發者在 `.claude/settings.json` 新增或修改任一 `hooks.<event>[].hooks[].command` 欄位
- **THEN** command 字串 SHALL 以 `$CLAUDE_PROJECT_DIR/.claude/hooks/` 為開頭，例如 `$CLAUDE_PROJECT_DIR/.claude/hooks/capture_user_prompt.py`

#### Scenario: 從 worktree session 觸發 hook 仍能正確執行

- **WHEN** 使用者在 `.claude/worktrees/<name>/` 下開的 Claude Code session 觸發任一 hook（SessionStart / UserPromptSubmit / SessionEnd / SubagentStart / SubagentStop / PostToolUseFailure），且該 worktree 的 branch 沒有 check in `.claude/hooks/` 檔案
- **THEN** 系統 SHALL 仍能執行主 repo `.claude/hooks/` 下對應的 hook 腳本，並寫入 `inbox/captured/cc_events/<session_id>/` 對應檔案；不應出現「No such file or directory」錯誤

#### Scenario: 違反規則的 settings.json 應在 review 時被識別

- **WHEN** 對 `.claude/settings.json` 執行 `grep -E '"command"\s*:\s*"\.claude/' .claude/settings.json` 或等價檢查
- **THEN** 結果 SHALL 為空（無相對路徑形式的 hook command）
