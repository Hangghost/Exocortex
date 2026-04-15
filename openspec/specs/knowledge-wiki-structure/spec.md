## ADDED Requirements

### Requirement: KnowledgeWiki repo 頂層結構
KnowledgeWiki SHALL 為獨立 git repo，包含以下頂層檔案與目錄：`raw/`、`summaries/`、`concepts/`、`AGENTS.md`、`reading_list.md`、`INDEX.md`、`INDEX_by_cluster.md`，以及 `periodic_jobs/wiki_compiler/`。

#### Scenario: 初始化後的完整結構驗證
- **WHEN** KnowledgeWiki repo 完成本次升級後
- **THEN** 應存在：`raw/`、`summaries/`、`concepts/`、`concepts/_map.md`、`AGENTS.md`、`reading_list.md`、`INDEX.md`、`INDEX_by_cluster.md`、`periodic_jobs/wiki_compiler/compiler.py`

### Requirement: raw/ 為未加工輸入區
`raw/` SHALL 只存放人工放入的原始知識文章（web clips、paper markdown、筆記等），不由任何腳本自動寫入。

#### Scenario: 手動放入 raw 文章
- **WHEN** 使用者將一篇 web clip 存入 `raw/`
- **THEN** 文章保持原始格式，不被任何自動流程修改

### Requirement: 文章使用標準 frontmatter
`raw/`、`summaries/`、`concepts/` 下的所有 `.md` 文章 SHALL 包含 YAML frontmatter，必填欄位：`title`、`date`。`raw/` 文章建議包含 `source`（原始 URL）；`summaries/` 文章 SHALL 包含 `source_file`（對應的 raw 文章路徑）；`concepts/` 文章 SHALL 包含 `sources`（清單，對應的 summaries 路徑）。

#### Scenario: Agent 讀取 summaries 文章
- **WHEN** agent 讀取 `summaries/` 中的文章
- **THEN** 可透過 `source_file` frontmatter 追溯至對應的 `raw/` 原文

#### Scenario: Obsidian 開啟 KnowledgeWiki 資料夾
- **WHEN** 使用者將 KnowledgeWiki 資料夾加入 Obsidian vault
- **THEN** `[[wikilinks]]` 可正常解析，graph view 顯示文章間的連結關係

### Requirement: INDEX.md 為 agent 的知識查詢入口
`INDEX.md` SHALL 列出 `concepts/` 中所有概念文章，每條目包含：概念名稱、一行摘要、對應的 concepts 路徑。

#### Scenario: Agent 查詢域知識
- **WHEN** agent 需要查詢特定主題的知識
- **THEN** agent 讀取 `INDEX.md` 找到相關概念，按需讀取對應的 `concepts/<topic>.md`，不需要讀取所有文章

### Requirement: wiki_compiler SHALL 提供工具集介面供 AI agent 呼叫
`periodic_jobs/wiki_compiler/compiler.py` SHALL 支援以下 subcommands，各自處理 deterministic 操作，供 AI agent 選擇性呼叫：
- `scan`：列出 raw/ 中尚未有對應 summary 的文章
- `extract-refs <path>`：從指定 raw 文章抽出外部連結，append 到 reading_list.md 引用佇列
- `reindex`：從 concepts/*.md 的 frontmatter 重建 INDEX.md 和 INDEX_by_cluster.md
- `validate`：檢查 frontmatter 必填欄位完整性、wikilinks 正確性、raw/summary 覆蓋率
- `status`：印出 raw/summary/concept 的數量與覆蓋率統計

#### Scenario: Agent 使用 scan 找待處理文章
- **WHEN** AI agent 執行 `python compiler.py scan`
- **THEN** 回傳尚未有對應 summaries/*.md 的 raw 文章路徑列表（結構化輸出，agent 可解析）

#### Scenario: Agent 使用 validate 做 QA
- **WHEN** AI agent 寫入或更新 concepts/*.md 後執行 `python compiler.py validate`
- **THEN** 回傳任何缺少必填 frontmatter 欄位的概念、broken wikilinks、以及未被任何 concept 對應的 raw 文章

#### Scenario: 無新文章時執行 scan
- **WHEN** 所有 raw/ 文章都已有對應 summaries/ 時執行 `python compiler.py scan`
- **THEN** 印出「無新文章需要處理」並結束，不修改任何文件
