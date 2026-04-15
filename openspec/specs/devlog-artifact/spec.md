# Spec: Devlog Artifact

## ADDED Requirements

### Requirement: devlog.md 是 openspec change 的標準文件
每個 openspec change 目錄 SHALL 支援 `devlog.md` 作為第四份標準文件，與 proposal.md、design.md、tasks.md 並列。devlog.md 記錄實作過程的敘事，不是設計文件，而是「發生了什麼」的紀錄。

#### Scenario: devlog.md schema 合規
- **WHEN** devlog.md 存在於 change 目錄
- **THEN** 檔案 MUST 包含 YAML frontmatter（`change`、`date` 欄位）以及以下五個 section：`## 為什麼做這個`、`## 實作過程摘要`、`## 踩過的坑`、`## 關鍵決策`、`## 可提煉的經驗`

#### Scenario: devlog.md 缺失時不阻斷流程
- **WHEN** change 目錄中沒有 devlog.md
- **THEN** opsx:archive 仍可正常執行，但 SHOULD 顯示提示訊息：「此 change 沒有 devlog.md，建議補寫以保留實作經驗」

### Requirement: opsx:apply 完成後 AI 引導填寫 devlog
`opsx:apply` skill 在所有 tasks 完成後 MUST 進入 devlog 填寫引導模式。

#### Scenario: apply 完成後自動引導
- **WHEN** opsx:apply 完成所有 tasks
- **THEN** AI MUST 詢問使用者是否填寫 devlog，並根據本次 apply 的變更內容（讀過的檔案、做的決策、遇到的問題）協助起草 devlog 初稿，等待使用者確認或補充後寫入檔案

#### Scenario: 使用者跳過 devlog 填寫
- **WHEN** 使用者在引導時選擇跳過
- **THEN** AI 接受並繼續，不重複詢問；devlog.md 不建立

### Requirement: CHANGELOG.md 記錄系統里程碑
根目錄 SHALL 存在 `CHANGELOG.md`，以里程碑為單位分組記錄已歸檔的 changes。

#### Scenario: CHANGELOG.md 格式合規
- **WHEN** 讀取根目錄 CHANGELOG.md
- **THEN** 文件 MUST 包含版本條目（格式：`## v<N>.<M> — <語意描述>（<日期>）`），每個版本條目下列出對應的 archive change 名稱

#### Scenario: 新增里程碑條目
- **WHEN** 使用者認為當前進度值得標記里程碑
- **THEN** 在 CHANGELOG.md 頂部新增版本條目，列出自上個版本以來歸檔的 changes
