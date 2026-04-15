# Spec: ctx:project Command

## Requirement: /ctx:project new creates a project interactively
`/ctx:project new` 指令 SHALL 透過互動式問答引導使用者建立新專案。

### Scenario: Interactive project creation flow
- **WHEN** 使用者執行 `/ctx:project new`
- **THEN** AI SHALL 依序執行：
  1. 詢問專案名稱（kebab-case）與一句話描述
  2. 建立 `projects/<name>/` 目錄與 `context/` 子目錄
  3. 詢問 6 個標準問題（見下方 Scenario）
  4. 根據使用者回答填入 `PROJECT.md`
  5. 更新 `projects/INDEX.md`，新增該專案條目

### Scenario: Standard questions during project creation
- **WHEN** AI 收集專案資訊
- **THEN** AI SHALL 詢問以下問題（使用者可跳過或稍後填入）：
  1. 這個專案的目標是什麼？
  2. 現在進展到哪裡？什麼已經 work，什麼還沒？
  3. 最近的下一步是什麼？
  4. 有哪些資料來源要追蹤？（Codebase 路徑、Jira ticket/project、OpenSpec change 名稱、其他文件）
  5. 有沒有已經決定不要再討論的事？（關鍵決策）
  6. 有沒有特殊的環境設定要記錄？（帳號、endpoints 等）

### Scenario: 資料來源 section created during new
- **WHEN** 使用者在問題 4 回答了資料來源資訊
- **THEN** AI SHALL 在 PROJECT.md 建立 `## 資料來源` section，將回答解析為結構化列表，並加入 Work Logs 預設條目

### Scenario: Partial answers accepted
- **WHEN** 使用者對某些問題回答「稍後填入」或跳過
- **THEN** AI SHALL 在 PROJECT.md 中為未填入的區塊保留佔位符，不阻止建立流程完成；跳過問題 4 時 `## 資料來源` 僅保留 Work Logs 預設條目

---

## Requirement: /ctx:project load brings project context into session
`/ctx:project load <name>` 指令 SHALL 讀取指定專案的 PROJECT.md 並將脈絡帶入目前 session。

### Scenario: Successful project load
- **WHEN** 使用者執行 `/ctx:project load <name>` 且 `projects/<name>/PROJECT.md` 存在
- **THEN** AI SHALL 讀取 PROJECT.md，並回報一個簡短的現況摘要（目標、現況、下一步）

### Scenario: Project not found
- **WHEN** 使用者執行 `/ctx:project load <name>` 但 `projects/<name>/` 不存在
- **THEN** AI SHALL 告知使用者專案不存在，並列出 `projects/INDEX.md` 中現有的專案名稱

### Scenario: Implicit project load via context
- **WHEN** 使用者在對話中提到某個已知專案名稱（如「繼續做 WWPF」）
- **THEN** AI SHOULD 主動讀取對應的 PROJECT.md 以取得工作脈絡，即使使用者未明確執行 load 指令

---

## Requirement: /ctx:project command is defined in .claude/commands/
`ctx:project` 指令 SHALL 定義在 `.claude/commands/ctx/project.md`，採用 Claude Code skill 格式。

### Scenario: Command file location
- **WHEN** 檢查 repo 結構
- **THEN** `.claude/commands/ctx/project.md` SHALL 存在，包含 `new`、`load`、`update`、`complete`、`pause`、`resume` 六個子命令的完整工作流說明

### Scenario: Subcommand routing
- **WHEN** 使用者執行 `/ctx:project` 並帶有子命令參數
- **THEN** AI SHALL 根據第一個參數路由至對應子命令：`new`、`load`、`update`、`complete`、`pause`、`resume`

### Scenario: Unknown subcommand or empty input
- **WHEN** 使用者執行 `/ctx:project` 無參數或帶不認識的子命令
- **THEN** AI SHALL 顯示所有六個子命令的使用說明，並讀取 `projects/INDEX.md` 列出現有專案

---

## Requirement: Smart-Gather queries Git as the primary source
`/ctx:project update` Smart-Gather 階段 SHALL 永遠執行 Git 查詢，無論 `## 資料來源` 中是否存在 OpenSpec 條目。Git log 是主線資料來源。

### Scenario: Git always queried regardless of OpenSpec presence
- **WHEN** PROJECT.md 的 `## 資料來源` 包含 OpenSpec 條目
- **THEN** Smart-Gather SHALL 執行 Git 查詢，不因 OpenSpec 存在而跳過

### Scenario: Git path sequential fallback
- **WHEN** `## 資料來源` 列出多個 Git path
- **THEN** Smart-Gather SHALL 依序嘗試每個路徑，第一個成功回傳結果的路徑即採用；路徑不可達時 SHALL 繼續嘗試下一個，不中斷流程

### Scenario: Local OpenSpec supplements Git results
- **WHEN** `## 資料來源` 的 OpenSpec 條目對應的 change 在 `openspec/changes/<name>/` 本地存在
- **THEN** Smart-Gather SHALL 讀取該 change 的 `tasks.md`，以任務完成度補充 Git 查詢結果；此資訊 SHALL 呈現為補充細節，不替代 Git log

### Scenario: External OpenSpec not fetched
- **WHEN** `## 資料來源` 的 OpenSpec 條目指向外部 repo（本地 `openspec/changes/<name>/` 不存在）
- **THEN** Smart-Gather SHALL NOT 嘗試讀取外部路徑；該條目視為狀態參考欄位，不執行主動查詢

---

## Requirement: Smart-Gather detects archived OpenSpec changes from Git log
Smart-Gather 完成 Git 查詢後，SHALL 掃描 Git log 中符合 `docs(openspec): archive` pattern 的 commit，識別已 archive 的 change name，並在呈現查詢結果時提示使用者確認是否更新 `## 資料來源`。

### Scenario: Archive commit detected in Git log
- **WHEN** Git log 包含 message 符合 `docs(openspec): archive <name>` pattern 的 commit
- **THEN** Smart-Gather SHALL 識別其中的 change name，並在查詢結果摘要後附加提示：「偵測到以下 changes 已 archived：[list]，要更新 ## 資料來源 嗎？」

### Scenario: User confirms archive state update
- **WHEN** 使用者確認更新
- **THEN** AI SHALL 在 PROJECT.md 的對應 OpenSpec 條目中，將該 change 標記為 `✅`，並記錄 archived date 與 commit SHA

### Scenario: User declines archive state update
- **WHEN** 使用者拒絕更新
- **THEN** AI SHALL NOT 修改 PROJECT.md，繼續 update 流程

### Scenario: No archive commits in Git log
- **WHEN** Git log 不包含任何 `docs(openspec): archive` commit
- **THEN** Smart-Gather SHALL NOT 顯示 archive 偵測提示
