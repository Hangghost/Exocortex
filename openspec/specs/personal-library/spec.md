# Spec: Personal Library

## Requirement: library/ 作為 AI-agent native 個人 library 的頂層目錄
`library/` SHALL 作為 Exocortex 的頂層目錄，存放使用者珍藏文章與個人文件的 markdown index cards。Binary 本體（PDF、PPTX 等）存放於 `~/Documents/AILibrary/`，不納入 git 版本控制。

### Scenario: library/ 目錄結構
- **WHEN** `library/` 目錄建立後
- **THEN** 目錄結構 SHALL 為：
  ```
  library/
  ├── INDEX.md          ← 所有 cards 的摘要索引表格
  ├── README.md         ← card 格式規範與新增流程
  └── <slug>.md         ← 每個珍藏項目的 index card
  ```

### Scenario: binary 檔案不放入 git repo
- **WHEN** 使用者新增 PDF、PPTX 等 binary 檔案到個人 library
- **THEN** binary 本體 SHALL 存放於 `~/Documents/AILibrary/<filename>`，只在 `library/<slug>.md` 的 `file_path` 欄位記錄絕對路徑

## Requirement: index card 格式統一
每個 `library/<slug>.md` SHALL 遵循標準 index card 格式，確保 AI 可快速判斷相關性。

### Scenario: index card frontmatter 必填欄位
- **WHEN** 建立一個新的 index card
- **THEN** 該檔案 frontmatter SHALL 包含以下欄位：
  - `title`：文章標題或文件名稱
  - `type`：`article`、`document`、`resume`、或 `reference` 之一
  - `date_saved`：YYYY-MM-DD 格式
  - `tags`：YAML 陣列，至少一個標籤

### Scenario: index card 可選欄位
- **WHEN** 建立文章類型（type: article）的 index card
- **THEN** SHOULD 包含 `source_url` 欄位（原始網址）

### Scenario: index card 有 binary 對應檔案時
- **WHEN** index card 對應到 `~/Documents/AILibrary/` 下的一個 binary 檔案
- **THEN** frontmatter SHALL 包含 `file_path: ~/Documents/AILibrary/<filename>`

### Scenario: index card 正文結構
- **WHEN** 建立 index card 正文
- **THEN** SHALL 包含 `## 摘要`（1-3 句）和 `## 標籤與關鍵字`（可被 grep 到的關鍵概念）

## Requirement: library/INDEX.md 提供快速全覽
`library/INDEX.md` SHALL 維護一個 markdown table，讓 AI 在不讀個別 card 的情況下快速判斷 library 的整體內容。

### Scenario: INDEX.md 表格欄位
- **WHEN** 查閱 `library/INDEX.md`
- **THEN** 表格 SHALL 包含欄位：標題、類型、儲存日期、標籤、Card 連結

### Scenario: 新增 card 後同步 INDEX.md
- **WHEN** 新增一個 `library/<slug>.md` card
- **THEN** `library/INDEX.md` SHALL 同步新增對應的 table row

## Requirement: registry/library.md 作為 library 路由入口
`registry/library.md` SHALL 指向 `library/INDEX.md` 和 `~/Documents/AILibrary/` 的路由說明，讓 AI 在執行跨系統任務前知道個人 library 的存取方式。

### Scenario: AI 尋找個人珍藏文章或文件
- **WHEN** AI 需要找使用者存過的文章或文件
- **THEN** SHALL 先查 `registry/library.md` 找到路由，再讀 `library/INDEX.md` 快速定位，再按需讀具體 card

### Scenario: registry/library.md 內容
- **WHEN** 查閱 `registry/library.md`
- **THEN** 文件 SHALL 包含：library/INDEX.md 路徑、~/Documents/AILibrary/ 路徑說明、card 格式簡述、未來 KnowledgeWiki 整合預留說明
