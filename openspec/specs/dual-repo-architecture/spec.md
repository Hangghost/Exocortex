# Spec: Dual-Repo Architecture

## Purpose

規範雙 repo 架構（private `exocortex-personal` + public `Exocortex`）的角色定義、git upstream remote 關係設定，以及里程碑驅動的架構同步觸發規則。確保個人資料層（private）與開源模板層（public）維持明確邊界，同步以 CHANGELOG 里程碑為單位而非逐 commit 跟隨。

## Requirements

### Requirement: Repo 角色定義
系統 SHALL 以兩個獨立 repo 運作：
- `Exocortex`（public）：通用架構模板，主開發場所，open-core upstream
- `exocortex-personal`（private）：個人 production 實例，downstream of `Exocortex`

#### Scenario: 識別哪個 repo 屬於哪個角色
- **WHEN** 使用者判斷一個檔案或變更屬於哪個 repo
- **THEN** 若該內容對任何使用者普遍有效（架構、工具、示範）→ 進 `Exocortex`；若該內容包含個人資料（身分、設備、個人記錄）→ 進 `exocortex-personal`

---

### Requirement: Git Upstream Remote 關係
`exocortex-personal` SHALL 將 public `Exocortex` 設為 upstream remote，命名為 `template`。

#### Scenario: 初始化 upstream 關係
- **WHEN** `exocortex-personal` 首次建立
- **THEN** 執行 `git remote add template <public-Exocortex-url>`，驗證 `git remote -v` 顯示 template remote

#### Scenario: 從 upstream 同步架構更新
- **WHEN** public `Exocortex` 有新的架構里程碑（對應一個 CHANGELOG 條目）
- **THEN** 在 `exocortex-personal` 執行 `git fetch template && git merge template/main`，合併通過後個人資料檔案不受影響

---

### Requirement: 里程碑驅動同步觸發
同步頻率 SHALL 以架構里程碑（CHANGELOG.md 的一個條目）為單位，而非每個 OpenSpec change。

#### Scenario: 判斷是否需要同步
- **WHEN** public `Exocortex` 的 CHANGELOG.md 新增一個里程碑條目
- **THEN** 這是一個應評估同步的觸發點；若里程碑涉及頂層結構變更（新目錄、新核心 rules 檔案），SHALL 同步到 `exocortex-personal`

---

### Requirement: 開發工作流——Private-first，透過 ctx:publish 發布
進行架構開發時，SHALL 在 `exocortex-personal` 中開發並測試，完成後透過 `ctx:publish` command 將架構改動發布到 public `Exocortex`。

#### Scenario: 在 private repo 開發架構變更
- **WHEN** 使用者設計一個通用架構改動
- **THEN** 在 `exocortex-personal` 中建立 openspec change、實作、測試（可利用真實個人資料驗證）；個人 openspec 設計記錄留在 `exocortex-personal/openspec/`

#### Scenario: 發布架構變更到 public template
- **WHEN** 架構變更在 private 完成並 archive
- **THEN** 執行 `ctx:publish`，選擇對應的 change，審閱 PUBLISH PLAN 後 apply 到 `~/Documents/Projects/Exocortex/` 並 commit

---

### Requirement: Publish 追蹤狀態
系統 SHALL 透過 `published.md` marker 追蹤每個 openspec change 是否已發布到 public template。

#### Scenario: 判斷 change 是否已發布
- **WHEN** 使用者或 command 需要知道某個 change 是否已 publish
- **THEN** 檢查 `openspec/changes/archive/<name>/published.md` 是否存在；存在 → 已發布，不存在 → 未發布

---

### Requirement: OpenSpec 歷史隔離
Public `Exocortex` 的 `openspec/changes/archive/` SHALL 從空白開始，不包含任何來自 `exocortex-personal` 的個人歷史。

#### Scenario: 第一次建立 public repo
- **WHEN** public `Exocortex` 初始化
- **THEN** `openspec/changes/archive/` 為空目錄（或不存在），private `exocortex-personal` 的 30+ archived changes 不遷移過去

#### Scenario: 未來架構變更進入 public
- **WHEN** 一個架構變更在 public `Exocortex` 完成並 archive
- **THEN** 該 change 的描述和 context 不含任何個人資料（設備名、帳號、個人專案名等）
