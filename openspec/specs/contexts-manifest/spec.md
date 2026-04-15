# Spec: Contexts Manifest

## Requirement: MANIFEST.md 定義 contexts/ 各子資料夾的觀察 schema
`contexts/MANIFEST.md` 是 `contexts/` 目錄的操作 schema 文件，職責範圍僅限 `contexts/` 下的子資料夾。系統 SHALL 在此文件中為每個子資料夾定義觀察行為，observer 在掃描前 SHALL 讀取此文件以決定每個資料夾的處理方式。`memory/` 已移出 `contexts/` 成為頂層目錄，不再是 MANIFEST.md 的管理對象。

### Scenario: observer 讀取 MANIFEST.md 決定觀察行為
- **WHEN** observer 執行掃描前
- **THEN** observer SHALL 讀取 `contexts/MANIFEST.md` 並依各資料夾的 `observation_mode` 決定處理方式

### Scenario: MANIFEST.md 包含必要欄位
- **WHEN** 在 MANIFEST.md 中定義一個子資料夾的 schema
- **THEN** 該 schema SHALL 包含 `observation_mode` 與 `extraction_focus` 兩個欄位

## Requirement: observation_mode 合法值與語意
每個子資料夾的 `observation_mode` SHALL 為下列值之一，語意明確：

- `ignore`：不掃描此資料夾（高重複、低資訊密度）
- `read_content`：讀取近期修改檔案的全文，提取觀察條目
- `read_content+personal_facts`：讀全文且額外執行 PersonalFacts 提取（見 KNOWLEDGE_BASE.md Section 8）
- `skip`：此資料夾是 observer 的輸出目標，不作為輸入來源

### Scenario: ignore 模式下不產生觀察條目
- **WHEN** 子資料夾的 `observation_mode` 為 `ignore`
- **THEN** observer SHALL 不讀取該資料夾任何檔案，不產生任何觀察條目

### Scenario: skip 模式下不讀取也不寫入（作為掃描來源）
- **WHEN** 子資料夾的 `observation_mode` 為 `skip`
- **THEN** observer SHALL 不將此資料夾納入掃描，僅作為寫入目標

## Requirement: 未定義資料夾的 fallback 行為
當 observer 遇到 `contexts/` 下存在但 MANIFEST.md 未定義的子資料夾時，系統 SHALL 執行預設 fallback。

### Scenario: 未定義資料夾觸發 fallback
- **WHEN** observer 掃描到 MANIFEST.md 中未定義的子資料夾
- **THEN** observer SHALL 以 `read_content` 模式處理，依 KNOWLEDGE_BASE.md §3.1 語意規範判斷優先級，並在觀察條目中記錄「此資料夾尚未在 MANIFEST.md 定義 schema」

## Requirement: MANIFEST.md 作為新增資料夾的設計參考
`contexts/MANIFEST.md` SHALL 包含「如何使用」說明段落，讓使用者或 AI 在新增子資料夾時有明確的設計準則可依循。

### Scenario: 新增資料夾時查閱 MANIFEST.md
- **WHEN** 需要在 `contexts/` 下新增子資料夾
- **THEN** MANIFEST.md 的說明段落 SHALL 提供足夠資訊讓使用者正確定義新資料夾的 schema

## Requirement: MANIFEST.md 不包含 memory/ 的 schema 條目
`memory/` 已從 `contexts/` 移出成為頂層目錄，因此 `contexts/MANIFEST.md` SHALL 不包含 `memory/` 的 schema 條目。`memory/` 的觀察設定不在 MANIFEST.md 管理範圍內。

### Scenario: MANIFEST.md 不含 memory 條目
- **WHEN** 查閱 `contexts/MANIFEST.md`
- **THEN** 文件中不出現 `memory/` 的 schema 條目；`memory/` 相關的說明應引導至 `rules/ARCHITECTURE.md`

### Scenario: Observer 不透過 MANIFEST.md 設定 memory/ 觀察
- **WHEN** observer 需要決定如何處理 `memory/`
- **THEN** observer 不在 MANIFEST.md 中找到 memory 的 `observation_mode`；`memory/` 作為 observer 的輸出目標，不作為掃描輸入來源

## Requirement: blog/ 的 observation schema 定義於 MANIFEST.md
`contexts/MANIFEST.md` SHALL 包含 `blog/` 子資料夾的 schema 條目，`observation_mode` 為 `read_content+personal_facts`。

### Scenario: MANIFEST.md 含 blog/ 條目
- **WHEN** 查閱 `contexts/MANIFEST.md`
- **THEN** 文件 SHALL 包含 `blog/` 的 schema 條目，`observation_mode: read_content+personal_facts`，`extraction_focus` 說明使用者主動思考的文章草稿與個人事實

### Scenario: blog/ 取代 daily_records/ 條目
- **WHEN** `contexts/MANIFEST.md` 完成更新
- **THEN** `daily_records/` 的條目 SHALL 移除，替換為 `blog/` 條目

## Requirement: survey_sessions/ 定義標準 frontmatter schema
`contexts/MANIFEST.md` 中 `survey_sessions/` 的 schema 條目 SHALL 新增 `frontmatter_schema` 欄位，定義標準 frontmatter 格式。

### Scenario: survey_sessions frontmatter 標準欄位
- **WHEN** 建立新的 survey session 檔案
- **THEN** frontmatter SHALL 包含以下欄位：
  - `date`: YYYY-MM-DD 格式
  - `topic`: 主題描述（一行）
  - `tags`: YAML 陣列

### Scenario: 舊 survey_sessions 檔案不強制更新
- **WHEN** `contexts/survey_sessions/` 下存在無 frontmatter 的舊檔案
- **THEN** 系統 SHALL NOT 強制要求 backfill；observer 對舊檔案使用現有 fallback 行為
