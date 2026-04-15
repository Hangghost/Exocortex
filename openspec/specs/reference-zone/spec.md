# Spec: Reference Zone

## Requirement: Reference zone directory exists
repo 根目錄 SHALL 包含 `_reference/` 目錄，作為所有「非活躍架構、待消化參考素材」的統一存放區。

### Scenario: Directory structure is correct
- **WHEN** repo 初始化後
- **THEN** `_reference/` 下應包含 `axioms/`、`playbooks/`、`tools/`、`jobs/` 子目錄

## Requirement: Reference zone is documented in WORKSPACE.md
WORKSPACE.md SHALL 包含對 `_reference/` 的說明，明確標注此目錄為「非架構，AI 不主動載入」；同時 WORKSPACE.md SHALL 包含 `registry/` 和 `state/` 兩個新目錄的路由條目，分別標注其用途。

### Scenario: AI reads WORKSPACE.md
- **WHEN** AI 在 session 啟動時讀取 WORKSPACE.md
- **THEN** AI 能識別 `_reference/` 的用途並知道不主動讀取其中內容
- **THEN** AI 能識別 `registry/` 為領域路由索引，知道在跨系統任務時應查詢
- **THEN** AI 能識別 `state/` 為即時狀態快照，知道在了解當前進度時應讀取

## Requirement: Active architecture directories are clean
`rules/`、`tools/`、`contexts/` SHALL 只包含實際在用的內容，不包含原作者特定的待評估素材。

### Scenario: tools/ contains only active tools
- **WHEN** 列出 `tools/` 目錄
- **THEN** 只應見到 `semantic_search/`、`send_email_to_myself.py`、`opencode_job.py`、`requirements.txt`

## Requirement: No broken playbook references in entry files
`AGENTS.md` 和 `CLAUDE.md` SHALL 不包含指向不存在路徑的 playbook 引用。

### Scenario: AI follows playbook reference
- **WHEN** AI 讀取 AGENTS.md 中的 playbook 引用
- **THEN** 每個引用路徑都應對應到實際存在的檔案
