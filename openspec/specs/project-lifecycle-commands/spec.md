# Spec: Project Lifecycle Commands

## Requirement: ctx:project update syncs progress and produces work_log
`/ctx:project update <name>` SHALL 先主動蒐集已知資料來源的進展資料，呈現查詢結果讓使用者確認，再以確認性問題引導使用者補充，最終更新 PROJECT.md 並產出 work_log。

### Scenario: Smart-gather phase — local sources
- **WHEN** 使用者執行 `/ctx:project update <name>` 且專案存在
- **THEN** AI SHALL 先執行以下查詢（不需使用者確認）：
  1. 讀取 `projects/<name>/PROJECT.md` 取得目前「現況」、「下一步」、`## 資料來源`
  2. 查詢 `contexts/work_logs/` 中 `project: <name>` 的近期條目（最近 5 筆）
  3. 若 `## 資料來源` 有 OpenSpec change：讀取對應 change 的 `proposal.md` 與 `tasks.md`
  4. 若 `## 資料來源` 有 Git 路徑且無 OpenSpec：查詢該 repo 近期 commits

### Scenario: Smart-gather phase — external sources require confirmation
- **WHEN** `## 資料來源` 包含 Jira ticket 或其他外部 API 來源
- **THEN** AI SHALL 詢問「偵測到 Jira 來源（<tickets>），要查詢嗎？[y/N]」，使用者確認後才執行查詢

### Scenario: Source query results presentation
- **WHEN** smart-gather 階段完成
- **THEN** AI SHALL 呈現：
  1. 已查詢的來源清單（格式：`✓ <source> — <brief finding>` 或 `✗ <source> — 未設定/未查詢`）
  2. 初步進展摘要（根據蒐集資料合成，盡力而為）
  3. 詢問「以上有沒有遺漏的來源？」

### Scenario: Confirmatory questions replace open-ended questions
- **WHEN** smart-gather 呈現完成
- **THEN** AI SHALL 詢問確認性問題（逐一，可跳過）：
  1. 「根據資料，進展如下：[草稿]，有要補充或修正嗎？」
  2. 「有學到什麼或踩到什麼坑？」（開放式）
  3. 「下一步有改變嗎？」（開放式）

### Scenario: Source gap detection from user answers
- **WHEN** 使用者在確認性問題中提到未登錄的來源（路徑、Jira key、OpenSpec change 名稱）
- **THEN** AI SHALL 識別後詢問「偵測到新來源 `<value>`，要加入 `## 資料來源` 嗎？[y/N]」，確認後寫入 PROJECT.md

### Scenario: 資料來源 absent on legacy project during update
- **WHEN** 執行 `update` 的專案 PROJECT.md 無 `## 資料來源` section
- **THEN** AI SHALL 僅查詢 work logs，嘗試 best-effort 解析 `## 材料地圖`，完成後提示「此專案尚未設定 `## 資料來源`，要建立嗎？[y/N]」，不阻斷流程

### Scenario: Project not found during update
- **WHEN** 使用者執行 `/ctx:project update <name>` 但 `projects/<name>/PROJECT.md` 不存在
- **THEN** AI SHALL 告知使用者專案不存在，並列出現有專案

### Scenario: Implicit update from conversation
- **WHEN** 使用者在對話中自然描述專案進度（如「QTAP 的新功能做完了」）
- **THEN** AI SHOULD 主動提議執行 update 流程，但 SHALL NOT 自動執行

---

## Requirement: ctx:project update produces structured work_log
每次 update SHALL 在 `contexts/work_logs/` 產出一份 work_log，作為 observer 觀察的橋樑。

### Scenario: Work_log file creation
- **WHEN** update 流程完成且使用者至少回答了一個確認性問題（非全部跳過）
- **THEN** AI SHALL 建立 `contexts/work_logs/YYYY-MM-DD_<project-name>_update.md`，包含：
  - 標題：`# <Project Name> — 進度更新`
  - `## 進展`：整合 smart-gather 資料與使用者補充後的完整進展
  - `## 經驗與觀察`：學到的東西或踩到的坑（若使用者有回答）
  - `## 下一步`：更新後的下一步
  - 未回答的 section 使用 `（未提供）` 佔位

### Scenario: All questions skipped
- **WHEN** 使用者跳過所有確認性問題
- **THEN** AI SHALL NOT 產出 work_log，僅更新 `last_updated`

### Scenario: Same-day multiple updates
- **WHEN** 同一天對同一專案執行多次 update
- **THEN** work_log 檔名 SHALL 加上序號後綴（如 `_update_2.md`）避免覆蓋

---

## Requirement: ctx:project complete triggers retrospective
`/ctx:project complete <name>` SHALL 引導使用者做專案回顧，產出 retrospective work_log，並將專案狀態改為 `completed`。

### Scenario: Complete flow with retrospective
- **WHEN** 使用者執行 `/ctx:project complete <name>` 且專案 status 為 `active` 或 `paused`
- **THEN** AI SHALL：
  1. 讀取 PROJECT.md 顯示專案摘要
  2. 詢問使用者五個回顧問題（可跳過）：
     - 這個專案最終達成了什麼？
     - 什麼做得好、值得未來重複？
     - 什麼做得不好或可以改進？
     - 有哪些意外的發現或學習？
     - 如果重來一次，會有什麼不同的做法？
  3. 產出 retrospective work_log
  4. 更新 PROJECT.md：status → `completed`，新增 `completed_date` frontmatter，更新 `last_updated`
  5. 更新 INDEX.md：status → `completed`，`last_updated` → 今天

### Scenario: Retrospective work_log creation
- **WHEN** complete 流程的回顧完成
- **THEN** AI SHALL 建立 `contexts/work_logs/YYYY-MM-DD_<project-name>_retrospective.md`，包含：
  - 標題：`# <Project Name> — 專案回顧`
  - `## 達成成果`
  - `## 成功經驗`（什麼值得重複）
  - `## 改進空間`（什麼可以做得更好）
  - `## 意外發現`
  - `## 如果重來`
  - 未回答的 section 使用 `（未提供）` 佔位

### Scenario: Complete with all questions skipped
- **WHEN** 使用者跳過所有回顧問題
- **THEN** AI SHALL 仍然建立 retrospective work_log（僅含標題和佔位符），並完成狀態變更

### Scenario: Complete already-completed project
- **WHEN** 使用者執行 `/ctx:project complete <name>` 但專案 status 已為 `completed` 或 `archived`
- **THEN** AI SHALL 告知使用者該專案已經完成，不重複執行回顧流程

---

## Requirement: ctx:project pause suspends a project
`/ctx:project pause <name>` SHALL 將專案狀態改為 `paused`。

### Scenario: Pause an active project
- **WHEN** 使用者執行 `/ctx:project pause <name>` 且專案 status 為 `active`
- **THEN** AI SHALL：
  1. 更新 PROJECT.md frontmatter：status → `paused`，`last_updated` → 今天
  2. 更新 INDEX.md 對應行：status → `paused`，`last_updated` → 今天
  3. 告知使用者專案已暫停，staleness check 將不再觸發

### Scenario: Pause non-active project
- **WHEN** 使用者執行 `/ctx:project pause <name>` 但專案 status 不是 `active`
- **THEN** AI SHALL 告知使用者目前狀態，建議適當的操作

---

## Requirement: ctx:project resume reactivates a paused project
`/ctx:project resume <name>` SHALL 將 `paused` 專案改回 `active`。

### Scenario: Resume a paused project
- **WHEN** 使用者執行 `/ctx:project resume <name>` 且專案 status 為 `paused`
- **THEN** AI SHALL：
  1. 更新 PROJECT.md frontmatter：status → `active`，`last_updated` → 今天
  2. 更新 INDEX.md 對應行：status → `active`，`last_updated` → 今天
  3. 讀取 PROJECT.md 顯示簡短現況摘要，協助使用者回到工作狀態

### Scenario: Resume non-paused project
- **WHEN** 使用者執行 `/ctx:project resume <name>` 但專案 status 不是 `paused`
- **THEN** AI SHALL 告知使用者目前狀態，建議適當的操作

---

## Requirement: Load and update prompt reactivation for paused projects
對 `paused` 專案執行 load 或 update 時，AI SHALL 提醒使用者考慮重新啟動。

### Scenario: Load a paused project
- **WHEN** 使用者執行 `/ctx:project load <name>` 且專案 status 為 `paused`
- **THEN** AI SHALL 正常載入脈絡，但在摘要末尾附加提醒：「此專案目前為暫停狀態。如果你準備繼續工作，可以用 `/ctx:project resume <name>` 重新啟動。」

### Scenario: Update a paused project
- **WHEN** 使用者執行 `/ctx:project update <name>` 且專案 status 為 `paused`
- **THEN** AI SHALL 正常執行 update 流程，但在完成後附加提醒：「此專案目前為暫停狀態，但你剛更新了進度。要改回 active 嗎？」並等待使用者確認

## Requirement: ctx:project rename 更新所有引用
`/ctx:project rename <old> <new>` SHALL 透過腳本執行確定性的批次重新命名，涵蓋目錄、索引，以及所有 contexts/ 下帶有 `project:` frontmatter 的檔案。

### Scenario: rename 觸發腳本執行
- **WHEN** 使用者執行 `/ctx:project rename <old> <new>`
- **THEN** AI SHALL：
  1. 確認 `projects/<old>/` 存在，`projects/<new>/` 不存在
  2. 執行 `python infra/tools/rename_project.py <old> <new>`
  3. 顯示腳本輸出（每步操作結果）
  4. 回報完成並列出已更新的檔案數量

### Scenario: rename 腳本的操作範圍
- **WHEN** `rename_project.py <old> <new>` 執行
- **THEN** 腳本 SHALL 依序執行：
  1. `mv projects/<old>/ projects/<new>/`
  2. 更新 `projects/INDEX.md` 的 name 欄
  3. batch-replace `project: <old>` → `project: <new>` in `contexts/work_logs/**`
  4. batch-replace `project: <old>` → `project: <new>` in `contexts/thought_review/**`
  5. batch-replace `project: <old>` → `project: <new>` in `contexts/blog/**`

### Scenario: rename 前置條件檢查失敗
- **WHEN** `projects/<old>/` 不存在，或 `projects/<new>/` 已存在
- **THEN** 腳本 SHALL 終止並回報錯誤，不執行任何 mv 或替換操作

### Scenario: rename 不涉及 openspec 文件
- **WHEN** `openspec/changes/` 下有引用舊專案名稱的文件
- **THEN** 腳本 SHALL 不修改 openspec/ 目錄下的任何檔案（openspec 以 change name 為鍵，與 project name 語意不同）
