## ADDED Requirements

### Requirement: web-clip skill 提供 KnowledgeWiki 作為輸出選項
web-clip skill 的輸出路徑選項 SHALL 包含 KnowledgeWiki `raw/` 作為可選目的地，讓使用者在 clip 時人工決定文章去向。

#### Scenario: Clip 文章並選擇存入 KnowledgeWiki
- **WHEN** 使用者執行 web-clip 並選擇 KnowledgeWiki 路徑
- **THEN** 文章存入 `KnowledgeWiki/raw/`，frontmatter 包含 `source`（原始 URL）和 `date`

#### Scenario: Clip 文章並選擇存入 Exocortex blog
- **WHEN** 使用者執行 web-clip 並選擇 Exocortex 路徑
- **THEN** 文章存入 `Exocortex/contexts/blog/<date>/`，行為與現有一致

### Requirement: 路由決策由人工完成，不自動分類
系統 SHALL NOT 自動判斷文章應進入 Exocortex 或 KnowledgeWiki，路由決策完全由使用者在 clip 時指定。

#### Scenario: 使用者未指定路由
- **WHEN** 使用者執行 web-clip 但未明確選擇目的地
- **THEN** 詢問使用者選擇，不預設自動路由
