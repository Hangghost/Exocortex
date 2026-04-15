## ADDED Requirements

### Requirement: System skills use AgentSkills standard format
`rules/skills/` 下的每個 skill SHALL 以子目錄形式存在，目錄名為 kebab-case skill 名稱，目錄內必須包含 `SKILL.md`，其 frontmatter 符合 AgentSkills 標準（必填欄位：`name`、`description`）。

#### Scenario: Valid skill structure
- **WHEN** 在 `rules/skills/` 下新增一個 skill
- **THEN** 目錄結構為 `rules/skills/<name>/SKILL.md`，且 SKILL.md 包含合法的 AgentSkills frontmatter

#### Scenario: Cross-agent portability
- **WHEN** 任何支援 AgentSkills 標準的 agent（Cursor、Gemini CLI、OpenCode 等）載入此 repo
- **THEN** 該 agent 能讀取並使用 `rules/skills/` 下的 skills，無需額外轉換

### Requirement: INDEX.md serves as the system skill manifest
`rules/skills/INDEX.md` SHALL以表格形式列出所有系統 skills 的 name 與 description，作為 session 啟動時的能力速查入口。每新增或刪除一個 skill，INDEX.md 必須同步更新——可透過執行 `infra/tools/sync-skill-index.py` 自動重建，或手動更新。

#### Scenario: Session startup skill discovery
- **WHEN** agent 在 session 啟動時讀取 `rules/skills/INDEX.md`
- **THEN** agent 能得知系統中所有可用 skills 的名稱與用途，無需逐一掃描子目錄

#### Scenario: INDEX.md stays lean
- **WHEN** 檢視 `rules/skills/INDEX.md` 的內容
- **THEN** 每個 skill 條目只包含名稱與一行 description，不嵌入完整 SKILL.md 內容

#### Scenario: INDEX.md can be rebuilt from source of truth
- **WHEN** `python infra/tools/sync-skill-index.py` 執行
- **THEN** INDEX.md 被重建，內容與所有 `rules/skills/*/SKILL.md` 的 frontmatter 一致

### Requirement: Progressive disclosure on skill loading
Agent 讀取系統 skill 時 SHALL 遵循三層 progressive disclosure：(1) INDEX.md metadata → (2) SKILL.md body（按需）→ (3) references/、scripts/、assets/ 內容（更按需）。

#### Scenario: Skill activated on demand
- **WHEN** agent 判斷某任務需要用到特定 skill
- **THEN** agent 讀取該 skill 的完整 SKILL.md，而非 session 啟動時就載入全部 skills

#### Scenario: Supplementary resources loaded as needed
- **WHEN** SKILL.md 內容引用 `references/` 或 `scripts/` 下的資源
- **THEN** agent 僅在執行需要時才讀取這些資源，不預先載入

### Requirement: Reflector promotes to rules/skills/
L2 Reflector 晉升工作流、最佳實踐類觀察時，SHALL 在 `rules/skills/` 下建立對應子目錄與 SKILL.md，並同步更新 `rules/skills/INDEX.md`。

#### Scenario: Reflector promotion creates valid skill
- **WHEN** reflector 將 OBSERVATIONS.md 中的高優觀察晉升為系統 skill
- **THEN** 在 `rules/skills/<name>/SKILL.md` 建立符合 AgentSkills 格式的檔案，且 INDEX.md 新增對應條目

### Requirement: System skills and agent skills are complementary
`rules/skills/`（系統 skills，repo 維護）與 agent-specific skills（如 `.claude/skills/`，agent 維護）SHALL 各自獨立存在，不強制合併。Agent 在 session 中應將兩者合併視為完整能力圖。

#### Scenario: Capability coverage with multiple agents
- **WHEN** 使用 Claude Code 開啟此 repo
- **THEN** agent 同時知悉 `rules/skills/`（系統 skills）和 `.claude/skills/`（Claude Code skills）

#### Scenario: Capability coverage with non-Claude agent
- **WHEN** 使用 Cursor 或 OpenCode 開啟此 repo
- **THEN** agent 仍能讀取 `rules/skills/` 中的系統 skills，即使其無 `.claude/skills/` 的對應能力
