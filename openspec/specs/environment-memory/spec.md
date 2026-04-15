## ADDED Requirements

### Requirement: Observer extracts personal facts from whitelisted directories
Observer SHALL 讀取 `contexts/survey_sessions/` 和 `contexts/thought_review/` 下的文件內容，識別並提取個人環境事實（設備、帳號架構、工具設定、工作流限制），寫入 OBSERVATIONS.md 作為結構化 `🟡 [PersonalFacts]` 觀測條目。

#### Scenario: New file in survey_sessions
- **WHEN** Observer 偵測到 `contexts/survey_sessions/` 下有新增或近期修改的文件
- **THEN** Observer 讀取該文件內容，提取個人環境事實，以 `🟡 [PersonalFacts]` 格式追加至 OBSERVATIONS.md

#### Scenario: File contains no personal facts
- **WHEN** Observer 讀取的文件不含設備、帳號、工具等個人環境事實
- **THEN** Observer 不寫入 `[PersonalFacts]` 條目，正常記錄一般觀測

#### Scenario: Personal facts format in OBSERVATIONS.md
- **WHEN** Observer 提取到個人事實
- **THEN** 寫入格式為：`🟡 [PersonalFacts] 來源：<相對路徑>`，後接縮排列點列出具體事實

### Requirement: Reflector promotes PersonalFacts observations to ENVIRONMENT.md
Reflector SHALL 識別 OBSERVATIONS.md 中的 `[PersonalFacts]` 觀測條目，並將其內容以 merge（非 append）方式更新至 `rules/ENVIRONMENT.md`。

#### Scenario: Reflector encounters PersonalFacts entry
- **WHEN** Reflector 讀取 OBSERVATIONS.md 並發現 `[PersonalFacts]` 條目
- **THEN** Reflector 將條目內的事實寫入 `rules/ENVIRONMENT.md` 對應類別區塊，相同類別的舊事實被新事實覆蓋

#### Scenario: Conflicting facts between old and new
- **WHEN** ENVIRONMENT.md 已有某類事實（如「設備」），新的 PersonalFacts 提供了不同內容
- **THEN** Reflector 以新事實取代舊事實，不保留矛盾的舊條目

### Requirement: ENVIRONMENT.md is loaded each session
`rules/ENVIRONMENT.md` SHALL 存在於 `rules/` 目錄下，並在每 session 啟動時由**所有 AI agent**讀取，使個人環境事實對 AI 可見。此需求從原本只適用於 CLAUDE.md session 協定，擴展為適用於所有入口（AGENTS.md 和 CLAUDE.md）。

#### Scenario: AI session starts via AGENTS.md
- **WHEN** 非 Claude Code 的 AI agent 開始新 session 並讀取 AGENTS.md
- **THEN** agent 透過 CORE.md 的 session 閱讀清單讀取 `rules/ENVIRONMENT.md`，取得使用者的設備、帳號架構、工具等環境基底事實

#### Scenario: AI session starts via CLAUDE.md
- **WHEN** Claude Code 開始新 session 並讀取 CLAUDE.md
- **THEN** agent 透過 CORE.md 的 session 閱讀清單讀取 `rules/ENVIRONMENT.md`，取得相同的環境事實

#### Scenario: ENVIRONMENT.md is empty or minimal on first run
- **WHEN** ENVIRONMENT.md 初始為空殼（僅有結構標題）
- **THEN** 首次 Reflector 跑完後，ENVIRONMENT.md 應包含從歷史文件提取的個人事實
