# Spec: Shared Agent Protocol

## Requirement: CORE.md is the single source of truth for shared agent behavior
`rules/CORE.md` SHALL 包含所有 AI agent 共享的行為規則，包含：session 閱讀清單、file routing 規則、memory system 架構、sub-agent 模型路由、Opus 工作模式、safety rules。

### Scenario: New session with any AI agent
- **WHEN** 任何 AI agent（Claude Code、OpenCode、Cursor 等）開始新 session 並讀取 AGENTS.md 或 CLAUDE.md
- **THEN** agent 被指示讀取 `rules/CORE.md`，取得完整的共享行為規則

### Scenario: Behavior consistency across tools
- **WHEN** 同一個 repo 被 Claude Code 和 OpenCode 各自開啟
- **THEN** 兩個 agent 在 session 協定、file routing、sub-agent 路由上表現一致，差異只在各自入口的獨有設定

## Requirement: AGENTS.md delegates to CORE.md and retains only agent-generic unique content
`AGENTS.md` SHALL 只包含：開場白語氣文字、CORE.md 讀取指令、skills 快查表（指向 `rules/skills/INDEX.md`）。不得包含任何已在 CORE.md 中存在的行為規則。

### Scenario: AGENTS.md content audit
- **WHEN** 審查 AGENTS.md 內容
- **THEN** 不應出現 OBSERVATIONS.md 路徑、observer.py、reflector.py、sub-agent 模型路由等屬於 CORE.md 的關鍵詞；skills 快查表應引用 `rules/skills/INDEX.md` 而非 `rules/playbooks/INDEX.md`

## Requirement: CLAUDE.md delegates to CORE.md and retains only Claude Code-specific content
`CLAUDE.md` SHALL 只包含：CORE.md 讀取指令、periodic jobs 執行指令、cron 設定參考、Claude Code hooks 相關設定。不得包含任何已在 CORE.md 中存在的行為規則。

### Scenario: CLAUDE.md content audit
- **WHEN** 審查 CLAUDE.md 內容
- **THEN** 不應出現重複的 session 閱讀清單、memory system 架構說明、sub-agent 路由等屬於 CORE.md 的內容

## Requirement: Pre-commit hook prevents drift
`.git/hooks/pre-commit` SHALL 在每次 commit 前檢查 AGENTS.md 和 CLAUDE.md 是否都包含對 `rules/CORE.md` 的引用。若任一檔案缺少引用，commit 被阻止並顯示警告。

### Scenario: Commit without CORE.md reference in AGENTS.md
- **WHEN** commit 包含對 AGENTS.md 的修改，且 AGENTS.md 不包含 `rules/CORE.md` 字串
- **THEN** pre-commit hook 輸出警告訊息並以非零 exit code 阻止 commit

### Scenario: Hook script is version-controlled
- **WHEN** 使用者在新機器上 clone repo
- **THEN** 可從 `.git-hooks/pre-commit` 取得 hook 腳本，執行安裝指令後立即生效

## Requirement: WORKSPACE.md 是純路由速查表
`rules/WORKSPACE.md` SHALL 只包含：目錄路由規則（各類內容放哪裡）、命名規則、Python 環境說明、快速查詢索引，以及查閱 ARCHITECTURE.md 的時機指引。不得包含設計意圖說明或各區塊的「為什麼」——這些內容屬於 `rules/ARCHITECTURE.md`。

### Scenario: WORKSPACE.md 內容審查
- **WHEN** 審查 WORKSPACE.md 內容
- **THEN** 不應出現解釋「為什麼這樣設計」的段落；所有路由條目只回答「去哪裡找/放什麼」

### Scenario: Agent 查閱路由
- **WHEN** AI agent 需要知道某類檔案放在哪個目錄
- **THEN** 在 WORKSPACE.md 快速找到對應路由條目，無需閱讀設計說明
