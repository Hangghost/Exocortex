## ADDED Requirements

### Requirement: KnowledgeWiki SHALL 包含 AGENTS.md 作為 AI agent 操作協定
`AGENTS.md` 位於 KnowledgeWiki repo 根目錄，包含：frontmatter 必填欄位定義、cluster 命名規範與新開條件、INDEX 維護規則、_map.md 更新規則、wiki_compiler 工具呼叫指引。任何 AI agent 讀取 AGENTS.md 後 SHALL 能執行正確的 wiki 操作。

#### Scenario: 新 AI agent session 處理 wiki
- **WHEN** 一個從未操作過 KnowledgeWiki 的 AI agent（Mastra、OpenCode、Claude Code）開始處理 wiki
- **THEN** agent 讀取 AGENTS.md 後應能正確決定 frontmatter 欄位、cluster 歸屬、INDEX 更新方式，無需額外人工指示

#### Scenario: AGENTS.md 包含 cluster 命名規範
- **WHEN** AI agent 需要決定一個新概念是否需要新 cluster
- **THEN** agent 可從 AGENTS.md 找到判斷準則（例如：至少 3 個概念才新開 cluster；cluster 名稱使用 kebab-case）

### Requirement: AGENTS.md SHALL 定義 wiki_compiler 工具的呼叫時機
AGENTS.md SHALL 列出 wiki_compiler 的所有 subcommand，說明每個指令的輸入、輸出、與適用場景，使 AI agent 知道何時呼叫哪個工具。

#### Scenario: Agent 完成寫入後觸發 reindex
- **WHEN** AI agent 寫入或更新任何 concepts/*.md 後
- **THEN** agent 應呼叫 `wiki_compiler.py reindex` 重建 INDEX 檔案

#### Scenario: Agent 處理新 raw 文章時觸發 extract-refs
- **WHEN** AI agent 處理一篇新 raw 文章後
- **THEN** agent 應呼叫 `wiki_compiler.py extract-refs <path>` 將外部連結寫入 reading_list.md
