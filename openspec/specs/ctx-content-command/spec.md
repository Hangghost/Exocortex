## ADDED Requirements

### Requirement: content/YYYY-MM-DD branch 永遠從 main 建立
`/ctx:content` 建立 `content/YYYY-MM-DD` branch 時 SHALL 永遠以 main 為 parent，無論當前在哪個 branch 執行。

#### Scenario: 首次建立當天 content branch
- **WHEN** `content/YYYY-MM-DD` 不存在
- **THEN** 系統 SHALL 執行 `git checkout main && git checkout -b content/YYYY-MM-DD`，確保新分支從 main HEAD 建立

#### Scenario: 當天 content branch 已存在
- **WHEN** `content/YYYY-MM-DD` 已存在
- **THEN** 系統 SHALL 直接執行 `git checkout content/YYYY-MM-DD`，不重新建立

---

### Requirement: 在 feature/* 上執行時自動重定向至 content branch
`/ctx:content` 偵測到目前在 `feature/*` branch 時 SHALL 自動將 content 提交到 `content/YYYY-MM-DD`，提交完成後切回原 feature branch。

#### Scenario: 在 feature/* 上執行，content branch 不存在
- **WHEN** 目前 branch 符合 `feature/*` 且 `content/YYYY-MM-DD` 不存在
- **THEN** 系統 SHALL 顯示「偵測到目前在 feature/X，content 將提交到 content/YYYY-MM-DD」，接著切到 main、建立 content/YYYY-MM-DD、執行 commit、切回 feature/X

#### Scenario: 在 feature/* 上執行，content branch 已存在
- **WHEN** 目前 branch 符合 `feature/*` 且 `content/YYYY-MM-DD` 已存在
- **THEN** 系統 SHALL 直接切到 content/YYYY-MM-DD、執行 commit、切回 feature/X

#### Scenario: 重定向後切回原 branch
- **WHEN** content commit 在 content/YYYY-MM-DD 完成
- **THEN** 系統 SHALL 自動切回原 feature/X，並顯示「已提交至 content/YYYY-MM-DD，已切回 feature/X」

---

### Requirement: 確認步驟壓縮為單次
`/ctx:content` 的確認流程 SHALL 只包含一次使用者確認：顯示待提交檔案清單與 commit message，按 Enter 執行。

#### Scenario: Arguments 已提供時跳過任務描述提問
- **WHEN** 使用者執行 `/ctx:content <description>`
- **THEN** 系統 SHALL 直接以 `<description>` 作為 commit message 語意 hint，不再詢問「任務是什麼」

#### Scenario: 單次確認格式
- **WHEN** 掃描完成、分支已就位
- **THEN** 系統 SHALL 顯示以下格式後等待 Enter：
  ```
  待提交：
    📁 <分類>  <檔案路徑>
    ...

  分支：content/YYYY-MM-DD
  Commit：<自動產生的 message>

  確認？[Enter]
  ```

---

### Requirement: merge 子命令作為 end-of-day 輕量合併入口
`/ctx:content merge` SHALL 將今天的 `content/YYYY-MM-DD` branch 合併到 main，跳過架構文件審查，保留 `--no-ff`。

#### Scenario: 執行 merge 子命令
- **WHEN** 使用者執行 `/ctx:content merge`
- **THEN** 系統 SHALL 執行以下步驟：
  1. 確認 `content/YYYY-MM-DD` 存在
  2. 若有未提交內容，先執行預設 commit 流程再繼續
  3. 顯示 commit 列表
  4. 確認後執行 `git checkout main && git merge --no-ff content/YYYY-MM-DD`
  5. 刪除 content/YYYY-MM-DD branch
  6. 顯示完成訊息

#### Scenario: 當天 content branch 不存在時的處理
- **WHEN** 使用者執行 `/ctx:content merge` 但 `content/YYYY-MM-DD` 不存在
- **THEN** 系統 SHALL 顯示「今天尚無 content/YYYY-MM-DD 分支」並結束，不執行任何 git 操作

#### Scenario: merge 子命令跳過架構文件審查
- **WHEN** `/ctx:content merge` 執行合併
- **THEN** 系統 SHALL NOT 執行 rules/WORKSPACE.md、AGENTS.md 等架構文件的審查步驟

#### Scenario: merge 子命令完成後提示
- **WHEN** 合併完成
- **THEN** 系統 SHALL 顯示「✓ 已合併 content/YYYY-MM-DD → main。若要 push：git push origin main」，並說明「架構 branch 請用 /ctx:merge」
