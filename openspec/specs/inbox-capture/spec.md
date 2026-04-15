# Spec: Inbox Capture

## Requirement: inbox/ 頂層目錄存在並包含標準結構
repo 根目錄 SHALL 包含 `inbox/` 目錄，其中包含 `todos.md`、`reading_list.md`、`ideas.md`、`README.md` 及 `captured/` 子目錄（含 `.gitkeep`）。

### Scenario: inbox 目錄結構完整
- **WHEN** repo 初始化後
- **THEN** `inbox/` 下應包含 `todos.md`、`reading_list.md`、`ideas.md`、`README.md`、`captured/.gitkeep`

### Scenario: README 說明各檔案用途與分流規則
- **WHEN** 使用者或 AI 讀取 `inbox/README.md`
- **THEN** README 應說明 inbox 是低門檻暫存區、各檔案的用途與格式、以及消化後的分流目標（`contexts/`、`projects/`、`openspec/changes/` 等）

## Requirement: inbox 是暫存區，不是最終存儲
`inbox/` SHALL 定位為「先記後整理」的低門檻捕獲區，消化後應將條目分流至適當的最終存儲。

### Scenario: 待辦事項捕獲
- **WHEN** 使用者記錄待辦事項
- **THEN** 記錄至 `inbox/todos.md`，消化後依類型移至 `projects/<name>/PROJECT.md` 或 `registry/life.md`

### Scenario: 閱讀清單捕獲
- **WHEN** 使用者記錄待讀文章或資源
- **THEN** 記錄至 `inbox/reading_list.md`，條目含 unread/done 狀態；讀後心得可分流至 `contexts/survey_sessions/` 或 KnowledgeWiki

### Scenario: 靈感捕獲
- **WHEN** 使用者記錄靈感或碎片想法
- **THEN** 記錄至 `inbox/ideas.md`；演化為具體提案後可移至 `openspec/changes/`（架構性）或 `projects/`（專案性）

### Scenario: 外部匯入的 raw notes
- **WHEN** 使用者從外部系統匯入原始筆記（如 Obsidian、截圖、語音轉文字）
- **THEN** 暫存至 `inbox/captured/`，消化整理後移至適當的最終存儲

## Requirement: WORKSPACE.md 說明 inbox 路由
`rules/WORKSPACE.md` SHALL 在知識與記錄路由區塊中說明 `inbox/` 的用途與適用場景。

### Scenario: AI 路由快速捕獲到 inbox
- **WHEN** AI 收到「記一下」、「先記」或「待辦」類型的請求
- **THEN** AI 在 WORKSPACE.md 中找到路由指引，將條目記錄至 inbox/ 下對應的檔案

## Requirement: Observer 可觀察 inbox 未處理狀態
observer 執行時 SHALL 能感知 `inbox/` 中的未處理條目數量，並在觀察條目中提醒使用者清理。

### Scenario: Observer 提醒 stale inbox 條目
- **WHEN** `inbox/todos.md` 或 `inbox/ideas.md` 中有超過一定時間未處理的條目
- **THEN** observer 在觀察輸出中記錄提醒，標注未清理的條目數量，但不強制清理
