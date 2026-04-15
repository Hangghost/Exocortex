# Spec: Context Registry

## Requirement: Registry directory exists with domain files
repo 根目錄 SHALL 包含 `registry/` 目錄，其中包含按領域組織的路由檔案。

### Scenario: Registry directory structure
- **WHEN** repo 初始化後
- **THEN** `registry/` 下應包含至少 `career.md`、`dev.md`、`life.md` 三個領域檔案

## Requirement: Registry files follow standard frontmatter format
每個 registry 檔案 SHALL 包含 YAML frontmatter，標記 `domain` 欄位。

### Scenario: AI reads a registry file
- **WHEN** AI 讀取 `registry/career.md`
- **THEN** AI 能解析 frontmatter 中的 `domain` 欄位，以及各段落下的資訊來源條目

## Requirement: Registry entries specify location and access method
每個 registry 條目 SHALL 說明資訊的存放位置（本機路徑或外部系統識別符）及存取方式。

### Scenario: Entry for local file
- **WHEN** registry 條目指向本機路徑
- **THEN** 條目應包含絕對路徑或相對於 HOME 的路徑，以及該來源包含的內容描述

### Scenario: Entry for external system via MCP
- **WHEN** registry 條目指向外部系統（如 Jira）
- **THEN** 條目應說明使用的 MCP tool 名稱及查詢方式（如 project key、過濾條件）

## Requirement: WORKSPACE.md documents registry directory
WORKSPACE.md SHALL 包含 `registry/` 目錄的說明，標注其用途為「領域路由索引」。

### Scenario: AI reads WORKSPACE.md and encounters registry reference
- **WHEN** AI 在 session 啟動時讀取 WORKSPACE.md
- **THEN** AI 能識別 `registry/` 的用途，並知道在任務需要跨系統上下文時應查詢對應領域檔案

## Requirement: WORKSPACE.md 路由規則反映 infra/ 命名空間
WORKSPACE.md 中的路由規則 SHALL 使用 `infra/` 前綴路徑，不含舊的頂層路徑（`tools/`、`periodic_jobs/`、`adhoc_jobs/`）。

### Scenario: AI 路由一次性專案
- **WHEN** AI 需要建立一次性分析或開發任務
- **THEN** AI 在 WORKSPACE.md 中找到路由指引為 `infra/adhoc_jobs/<project>/`，而非舊的 `adhoc_jobs/<project>/`

### Scenario: AI 路由工具指令碼
- **WHEN** AI 需要新增可複用工具指令碼
- **THEN** AI 在 WORKSPACE.md 中找到路由指引為 `infra/tools/`，而非舊的 `tools/`

### Scenario: AI 路由定時任務
- **WHEN** AI 需要查閱或修改定時任務
- **THEN** AI 在 WORKSPACE.md 中找到路由指引為 `infra/periodic_jobs/`，而非舊的 `periodic_jobs/`

## Requirement: WORKSPACE.md 路由規則包含 inbox/ 路徑
WORKSPACE.md 中 SHALL 包含 `inbox/` 的路由規則，說明快速捕獲的使用場景。

### Scenario: AI 路由快速捕獲請求
- **WHEN** AI 收到「快速記錄」、「先記一下」、「待辦」、「靈感」類型的請求
- **THEN** AI 在 WORKSPACE.md 中找到路由指引，將內容記錄至 `inbox/` 下對應的檔案（todos.md、reading_list.md、ideas.md 或 captured/）

## Requirement: WORKSPACE.md 不含 docs/ 路徑引用
`docs/` 目錄已解散，WORKSPACE.md SHALL 不包含任何指向 `docs/` 的路由條目或說明。

### Scenario: 查閱 WORKSPACE.md 時不出現 docs/ 路由
- **WHEN** AI 讀取 WORKSPACE.md
- **THEN** 文件中不出現 `docs/` 路徑；原 `docs/CRONTAB.md` 對應路由為 `infra/periodic_jobs/CRONTAB.md`

## Requirement: CLAUDE.md session start protocol includes registry
CLAUDE.md 的 Session Start Protocol SHALL 說明如何按任務類型查詢 registry。

### Scenario: AI starts a session with a domain-specific task
- **WHEN** 使用者提出跨系統任務（如「更新履歷」、「繼續 WWPF 開發」）
- **THEN** AI 應查詢 registry/ 中對應領域的路由檔案，找到相關資訊來源後再執行任務

## Requirement: registry/knowledge.md 指向 KnowledgeWiki
`Exocortex/registry/knowledge.md` SHALL 存在，記錄 KnowledgeWiki 的本機路徑與查詢入口（INDEX.md 位置）。

### Scenario: Agent 需要查詢域知識
- **WHEN** agent 在任務中需要查詢特定技術或概念的背景知識
- **THEN** agent 讀取 `registry/knowledge.md`，找到 KnowledgeWiki 的 INDEX.md 路徑，再按需讀取相關 concepts 文章

## Requirement: WORKSPACE.md 說明 KnowledgeWiki 路由
`rules/WORKSPACE.md` SHALL 在知識與記錄路由區塊中說明 KnowledgeWiki 的存在與查詢方式。

### Scenario: Agent 在 session 啟動時讀取 WORKSPACE.md
- **WHEN** agent 讀取 WORKSPACE.md
- **THEN** agent 知道「域知識查詢 → registry/knowledge.md → KnowledgeWiki/INDEX.md」的查詢路徑
