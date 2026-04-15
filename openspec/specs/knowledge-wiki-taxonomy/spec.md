## ADDED Requirements

### Requirement: Concepts frontmatter SHALL 包含 taxonomy 欄位
所有 `concepts/*.md` SHALL 在 YAML frontmatter 中包含以下欄位：
- `topics`（list）：細粒度標籤，多值
- `cluster`（string）：概念所屬主要群組，單值，kebab-case
- `related`（list）：相關概念的 wikilinks（`[[concept-name]]` 格式）

#### Scenario: AI agent 寫入新 concept
- **WHEN** AI agent 建立一篇新 concepts/*.md
- **THEN** frontmatter 必須包含 topics、cluster、related 三個欄位；`wiki_compiler.py validate` 執行後不回報缺欄位錯誤

#### Scenario: Agent 透過 metadata 決定 taxonomy
- **WHEN** AI agent 需要決定一個新概念的 cluster
- **THEN** agent 讀取現有 concepts/_map.md 了解現有 cluster，依 AGENTS.md 規範決定歸屬或新開 cluster，不需要移動任何檔案

### Requirement: KnowledgeWiki SHALL 包含 concepts/_map.md 作為 cluster 關係圖
`concepts/_map.md` 由 AI agent 維護，記錄 cluster 之間的關係（父子、同級、cross-domain bridge）與每個 cluster 所含的概念列表。使用 wikilinks 格式，與 Obsidian graph view 相容。

#### Scenario: AI agent 新增 cluster 後更新 _map.md
- **WHEN** AI agent 決定新開一個 cluster
- **THEN** agent 在 _map.md 新增該 cluster 的條目，包含至少一個概念 wikilink 和與其他 cluster 的關係描述

#### Scenario: Obsidian 開啟 KnowledgeWiki 時顯示 cluster 圖
- **WHEN** 使用者在 Obsidian 開啟 KnowledgeWiki 資料夾
- **THEN** graph view 可顯示 concepts 之間的 related 連結，_map.md 中的 wikilinks 可正常解析

### Requirement: KnowledgeWiki SHALL 包含 INDEX_by_cluster.md 作為分群導航入口
`INDEX_by_cluster.md` 由 `wiki_compiler.py reindex` 自動從 concepts frontmatter 的 cluster 欄位生成，以 cluster 為 section header 列出所屬概念。

#### Scenario: 規模化後的 cluster 導航
- **WHEN** KnowledgeWiki 包含 50+ concepts 且 agent/使用者需要找特定主題的概念
- **THEN** 讀取 INDEX_by_cluster.md 可按 cluster 快速縮小範圍，再按需展開 concepts/*.md

#### Scenario: 新 concept 加入後 INDEX_by_cluster 自動更新
- **WHEN** AI agent 執行 `wiki_compiler.py reindex`
- **THEN** INDEX_by_cluster.md 依所有 concepts 的 cluster frontmatter 欄位重新生成，無需手動維護
