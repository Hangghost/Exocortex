# Spec: Observer OpenSpec Scanning

## Requirement: Observer 掃描 openspec 歸檔目錄

Observer SOP（KNOWLEDGE_BASE.md）SHALL 包含 openspec 歸檔掃描規則。每次 observer 執行時，MUST 檢查 `openspec/changes/archive/` 下目錄名前綴符合 `target_date`（`YYYY-MM-DD-*`）的子目錄，對每個符合項目讀取其 `proposal.md`、`design.md`，以及（若存在）`devlog.md`，並產生 `[OpenSpec]` 觀察條目寫入 `memory/OBSERVATIONS.md`。

### Scenario: 當天有 openspec 歸檔

- **WHEN** `openspec/changes/archive/` 下存在目錄名前綴為 `target_date` 的子目錄
- **THEN** observer 讀取該目錄的 `proposal.md`（變更摘要）、`design.md`（關鍵技術決策）與 `devlog.md`（實作經驗，若存在），產生包含 `[OpenSpec]` 標籤的觀察條目，並 append 到 `OBSERVATIONS.md`

### Scenario: 當天沒有 openspec 歸檔

- **WHEN** `openspec/changes/archive/` 下不存在目錄名前綴為 `target_date` 的子目錄
- **THEN** observer 不產生任何 openspec 觀察條目（不寫入 OBSERVATIONS.md）

### Scenario: proposal.md 不存在於歸檔目錄

- **WHEN** 符合日期前綴的歸檔目錄中沒有 `proposal.md`
- **THEN** observer 記錄一條 🟢 Low 觀察說明該歸檔目錄缺少 proposal.md，並繼續處理其他條目

### Scenario: design.md 不存在於歸檔目錄

- **WHEN** 符合日期前綴的歸檔目錄中沒有 `design.md`
- **THEN** observer 僅從 `proposal.md` 提取摘要，不因缺少 design.md 而中斷，觀察條目中不包含技術決策段落

### Scenario: devlog.md 不存在於歸檔目錄

- **WHEN** 符合日期前綴的歸檔目錄中沒有 `devlog.md`
- **THEN** observer 正常產生觀察條目，僅略過 devlog 相關段落，不中斷、不報錯

## Requirement: [OpenSpec] 觀察條目格式

觀察條目 MUST 使用 `[OpenSpec]` 標籤，包含 change 名稱（去除日期前綴）、從 proposal.md 提取的變更摘要（What Changes、Capabilities）、從 design.md 提取的關鍵技術決策（Decisions 區塊），以及（若 devlog.md 存在）從 devlog.md 提取的「踩過的坑」與「可提煉的經驗」兩個 section 的摘要。優先級 SHALL 由 observer 依 KNOWLEDGE_BASE.md §3.1 語意規則綜合 proposal、design 與 devlog 內容自行判斷，不得預設固定值。

### Scenario: 標準觀察條目產生（含 design.md 與 devlog.md）

- **WHEN** observer 成功讀取 `proposal.md`、`design.md` 與 `devlog.md`
- **THEN** 產生格式為 `{emoji} [OpenSpec] 架構變更完成：{change-name}` 的觀察條目，包含變更摘要、關鍵技術決策，以及踩坑紀錄與可提煉的經驗

### Scenario: 標準觀察條目產生（無 devlog.md）

- **WHEN** observer 成功讀取 `proposal.md` 與 `design.md`，但 `devlog.md` 不存在
- **THEN** 產生格式為 `{emoji} [OpenSpec] 架構變更完成：{change-name}` 的觀察條目，包含變更摘要與關鍵技術決策，不包含踩坑與經驗段落

### Scenario: 優先級語意判斷

- **WHEN** proposal.md、design.md 或 devlog.md 描述跨模組架構重構、核心規則變更、或具跨專案通用價值的方法論決策
- **THEN** observer 判斷為 🔴 High

- **WHEN** proposal.md、design.md 或 devlog.md 描述新增功能、局部模組調整、或活躍專案里程碑
- **THEN** observer 判斷為 🟡 Medium

- **WHEN** proposal.md、design.md 或 devlog.md 描述小型 SOP 調整或文件更新
- **THEN** observer 判斷為 🟢 Low
