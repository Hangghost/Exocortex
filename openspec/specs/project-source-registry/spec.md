# Spec: Project Source Registry

## Requirement: PROJECT.md contains a structured 資料來源 section
每個專案的 `PROJECT.md` MAY 包含 `## 資料來源` section，以 markdown 列表記錄關聯的資料來源。

### Scenario: 資料來源 section format
- **WHEN** `## 資料來源` section 存在於 PROJECT.md
- **THEN** 內容 SHALL 為 markdown 列表，每行格式為 `- **<type>**: <value>`，支援的 type 包含：`Git`、`Jira`、`OpenSpec`、`Work Logs`、`其他`

### Scenario: Work Logs entry is always present
- **WHEN** `## 資料來源` section 建立時
- **THEN** `- **Work Logs**: 自動（\`project: <name>\`）` SHALL 被包含，代表 work logs 永遠被查詢

### Scenario: 資料來源 section absent on legacy projects
- **WHEN** PROJECT.md 不存在 `## 資料來源` section
- **THEN** AI SHALL NOT 拒絕執行 load 或 update 操作；`update` 流程應以 work logs 為唯一來源繼續，並在流程末尾提示使用者是否要建立資料來源登錄

---

## Requirement: AI can add new sources to 資料來源 during update
`/ctx:project update` 流程中，若偵測到使用者提及未登錄的資料來源，AI SHALL 詢問是否加入 `## 資料來源`。

### Scenario: New source detected in user's answer
- **WHEN** 使用者在 update 確認問題的回答中提到未登錄的路徑、Jira ticket、或 OpenSpec change
- **THEN** AI SHALL 識別潛在新來源，詢問「偵測到新來源 `<value>`，要加入 `## 資料來源` 嗎？[y/N]」

### Scenario: User confirms new source
- **WHEN** 使用者確認加入新來源
- **THEN** AI SHALL 在 PROJECT.md 的 `## 資料來源` section 追加一行 `- **<type>**: <value>`

### Scenario: User declines new source
- **WHEN** 使用者拒絕加入新來源
- **THEN** AI SHALL NOT 修改 `## 資料來源`，繼續 update 流程

---

## Requirement: OpenSpec entry supports structured state sub-format
`## 資料來源` 中的 OpenSpec 條目 MAY 使用結構化狀態子格式，以追蹤各 change 的完成狀態。

### Scenario: OpenSpec entry with state sub-format
- **WHEN** `## 資料來源` 包含 OpenSpec 條目且使用狀態子格式
- **THEN** 格式 SHALL 為：
  ```
  - **OpenSpec** (<label>):
    - ✅ `<change-name>` — archived <YYYY-MM-DD>, commit `<sha>`
    - 🔄 `<change-name>` — started <YYYY-MM-DD>, last commit `<sha>` (<YYYY-MM-DD>)
    - ⬜ `<change-name>` — planned
  ```
  其中 `<label>` 為 repo 或專案識別名稱（如 `qt-ap`）

### Scenario: State emoji semantics
- **WHEN** OpenSpec 條目含有狀態 emoji
- **THEN** SHALL 遵循以下語意：
  - `✅` = change 已完成並 archived，欄位含 archived date 與 commit SHA
  - `🔄` = change 進行中，欄位含 started date 與最新 commit SHA 及日期
  - `⬜` = change 已規劃但尚未開始

### Scenario: Legacy OpenSpec entry without state sub-format
- **WHEN** OpenSpec 條目為舊格式（無 ✅/🔄/⬜ 標記）
- **THEN** AI SHALL 視為未知狀態，不嘗試解析；在 Smart-Gather 偵測到相關 archive commit 時，以新格式覆寫或補充該條目（需使用者確認）
