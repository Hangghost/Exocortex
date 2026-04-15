# Spec: Project Context Layer

## Requirement: projects/ directory exists with INDEX.md
Repo 根目錄 SHALL 包含 `projects/` 目錄，以及 `projects/INDEX.md` 作為所有專案的一覽索引。

### Scenario: Index file structure
- **WHEN** `projects/INDEX.md` 存在
- **THEN** 每個專案佔一行，包含：name、status（`active` / `paused` / `completed` / `archived`）、last_updated（YYYY-MM-DD）、一句話描述

### Scenario: AI reads project list
- **WHEN** AI 需要了解目前進行中的專案
- **THEN** AI 應讀取 `projects/INDEX.md` 取得概覽，而非翻查 OBSERVATIONS.md 或其他位置

---

## Requirement: Each project has a PROJECT.md with standard sections
每個專案 SHALL 在 `projects/<name>/PROJECT.md` 中包含以下必要區塊：目標/動機、現況、下一步、關鍵決策、材料地圖、資料來源。

### Scenario: PROJECT.md content validation
- **WHEN** AI 執行 `/ctx:project load <name>`
- **THEN** AI 可從 PROJECT.md 中識別：這個專案要達到什麼目標、現在的狀態是什麼、最近要做什麼、有哪些決定不需要重新討論、相關材料在哪裡、有哪些資料來源可供 update 查詢

### Scenario: Materials remain in original locations
- **WHEN** 專案有相關的 work_logs、surveys、code
- **THEN** 這些材料 SHALL 保留在原有位置（contexts/、adhoc_jobs/ 等），PROJECT.md 只記錄路徑指針

### Scenario: Legacy PROJECT.md without 資料來源 section
- **WHEN** 舊 PROJECT.md 不存在 `## 資料來源` section
- **THEN** AI SHALL 仍能執行 load 與 update，不因缺少此 section 而中斷；`update` 時提示使用者建立

---

## Requirement: Projects support on-demand context via context/ subdirectory
每個專案 MAY 包含 `projects/<name>/context/` 子目錄，存放按需載入的深度技術文件。

### Scenario: AI fetches deeper context when needed
- **WHEN** 使用者的問題需要 PROJECT.md 中未涵蓋的技術細節
- **THEN** AI 應自行判斷並讀取 `projects/<name>/context/` 下的相關文件（如 technical.md、environment.md）

### Scenario: Passive loading excludes context/ files
- **WHEN** AI 執行 `/ctx:project load <name>`
- **THEN** 僅讀取 `PROJECT.md`；`context/` 下的文件 SHALL NOT 被自動載入

---

## Requirement: project names use kebab-case
`projects/` 下的每個專案目錄名稱 SHALL 使用 kebab-case（例如：`my-api`、`exocortex`）。

### Scenario: Directory naming convention
- **WHEN** 建立新專案目錄
- **THEN** 目錄名稱 SHALL 為全小寫、以連字號分隔的 kebab-case 字串

---

## Requirement: PROJECT.md last_updated is maintained
`PROJECT.md` 的 frontmatter SHALL 包含 `last_updated` 和 `status` 欄位，並在每次有意義的更新後更新。

### Scenario: Observer staleness detection
- **WHEN** Observer 執行每日掃描，發現 `projects/INDEX.md` 中某專案的 `last_updated` 超過 14 天
- **THEN** Observer SHALL 僅對 `status == "active"` 的專案寫入 🟡 Medium 觀測提醒。`paused`、`completed`、`archived` 狀態的專案 SHALL NOT 觸發 staleness 警告

### Scenario: Completed project has completed_date
- **WHEN** 專案透過 `/ctx:project complete` 標記為 completed
- **THEN** PROJECT.md frontmatter SHALL 新增 `completed_date: YYYY-MM-DD` 欄位，記錄完成日期
