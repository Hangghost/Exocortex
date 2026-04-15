# Spec: Blog Context

## Requirement: contexts/blog/ 取代 contexts/daily_records/ 作為主動寫作存放區
`contexts/blog/` SHALL 成為使用者主動思考後的文章草稿存放位置。語意定義：AI 草稿 → 使用者修改 → 發文前的存儲。此資料夾是系統中觀察價值最高的內容層。

### Scenario: 文章寫作工作流
- **WHEN** 使用者請 AI 產出文章草稿，並修改後確認
- **THEN** 最終文稿 SHALL 存放於 `contexts/blog/YYYY-MM-DD_<slug>.md`，與其他 contexts/ 內容使用相同命名慣例

### Scenario: 目錄不存在時自動建立
- **WHEN** 使用者首次存放文章且 `contexts/blog/` 目錄不存在
- **THEN** AI SHALL 建立目錄後寫入檔案

## Requirement: blog/ 的 observer observation_mode 為 read_content+personal_facts
`contexts/MANIFEST.md` 中 `blog/` 的 `observation_mode` SHALL 設定為 `read_content+personal_facts`，讓 observer 讀取全文並額外執行 PersonalFacts 提取。

### Scenario: observer 掃描 blog/ 下的近期文章
- **WHEN** observer 執行每日掃描且 `blog/` 下有近期修改的檔案
- **THEN** observer SHALL 讀取這些檔案全文，提取觀察條目，並執行 PersonalFacts 提取（依 KNOWLEDGE_BASE.md Section 8 定義）

### Scenario: 舊有 daily_records/ 檔案的路由
- **WHEN** `contexts/daily_records/` 目錄下仍有舊檔案（遷移期間）
- **THEN** 這些檔案 SHALL 透過 git mv 遷移至 `contexts/blog/`，不保留 daily_records/ 目錄

## Requirement: 路由文件反映 blog/ 的語意
WORKSPACE.md 和 ARCHITECTURE.md 中所有 `daily_records/` 的路由條目 SHALL 更新為 `blog/`，並附上新的語意說明。

### Scenario: WORKSPACE.md 路由查詢 blog/
- **WHEN** AI 需要決定主動寫作文章存放位置
- **THEN** 查詢 WORKSPACE.md 後 SHALL 指向 `contexts/blog/`，說明為「部落格文章草稿與思考產物」

### Scenario: ctx:content skill 識別 blog/ 類型
- **WHEN** `ctx:content` 掃描待提交內容
- **THEN** `contexts/blog/` 下的檔案 SHALL 被分類為 **Blog Posts**（取代舊的 Daily Records 分類）
