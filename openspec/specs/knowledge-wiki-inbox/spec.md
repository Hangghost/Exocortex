## ADDED Requirements

### Requirement: KnowledgeWiki SHALL 包含 reading_list.md 作為三用 inbox
`reading_list.md` 位於 KnowledgeWiki repo 根目錄，包含三個 section：
1. **未讀佇列**：使用者手動加入的待閱讀文章
2. **引用佇列**：AI agent 從 raw/ 文章掃出的外部連結
3. **Linting 建議**：AI linting 發現的知識缺口，建議可 clip 的補充資料

使用者是唯一的 curation 決策者：review reading_list.md → 決定 clip → 手動移入 raw/

#### Scenario: AI agent 掃出引用連結
- **WHEN** AI agent 執行 `wiki_compiler.py extract-refs <raw-article-path>`
- **THEN** raw 文章中所有外部連結被 append 到 reading_list.md 的「引用佇列」section，格式包含來源文章路徑

#### Scenario: 使用者review 並決定 clip
- **WHEN** 使用者審閱 reading_list.md 的引用佇列
- **THEN** 使用者可決定哪些連結值得 clip，手動執行 clip 並移入 raw/；不感興趣的條目可直接刪除

#### Scenario: 未讀文章在閱讀前暫存
- **WHEN** 使用者看到一篇文章但尚未決定是否要 clip 進 KnowledgeWiki
- **THEN** 可手動加入 reading_list.md 未讀佇列，作為「待考慮」暫存區

### Requirement: reading_list.md 的條目格式 SHALL 包含來源資訊
引用佇列的每個條目 SHALL 包含：文章標題（或 URL）、以及 cited-in 欄位標記來源 raw 文章。

#### Scenario: Agent 讀取引用佇列追溯來源
- **WHEN** agent 讀取 reading_list.md 的引用佇列
- **THEN** 可透過 cited-in 欄位找到是哪篇 raw 文章引用了這個連結，不需要重新掃描所有 raw 文章
