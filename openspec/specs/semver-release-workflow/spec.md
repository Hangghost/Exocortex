# Spec: SemVer Release Workflow

## ADDED Requirements

### Requirement: CHANGELOG 偵測觸發版號流程
系統 SHALL 在 ctx:merge 的 Step 2（文件審查）中，掃描 feature branch diff 是否包含 CHANGELOG.md 的修改。若偵測到，SHALL 解析新增的版號條目並在 Step 5.5 觸發版號確認流程。

#### Scenario: CHANGELOG 有修改時觸發
- **WHEN** `git diff main...HEAD --name-only` 結果包含 `CHANGELOG.md`
- **THEN** 系統 SHALL 解析 CHANGELOG.md 中最新的版號條目（格式 `## X.Y.Z — 描述`）並顯示於文件審查結果中，標記為「合併後將詢問是否打 tag」

#### Scenario: CHANGELOG 無修改時不觸發
- **WHEN** `git diff main...HEAD --name-only` 結果不包含 `CHANGELOG.md`
- **THEN** 系統 SHALL 跳過所有版號相關步驟，merge 流程維持原有行為

#### Scenario: 版號解析失敗時 fallback
- **WHEN** CHANGELOG.md 有修改但無法解析出符合 `\d+\.\d+\.\d+` 格式的版號
- **THEN** 系統 SHALL 在 Step 5.5 詢問使用者手動輸入版號，不中斷流程

---

### Requirement: Branch 前綴推斷 bump 類型
系統 SHALL 依 feature branch 的命名前綴自動推斷 SemVer bump 類型，並在詢問時作為預設建議。

#### Scenario: feature/* branch 建議 MINOR bump
- **WHEN** branch 名稱以 `feature/` 開頭
- **THEN** 系統 SHALL 建議 MINOR bump（X.Y.0，Y+1），並顯示新舊版號對比

#### Scenario: fix/* branch 建議 PATCH bump
- **WHEN** branch 名稱以 `fix/` 開頭
- **THEN** 系統 SHALL 建議 PATCH bump（X.Y.Z，Z+1），並顯示新舊版號對比

#### Scenario: 其他前綴詢問使用者
- **WHEN** branch 名稱不以 `feature/` 或 `fix/` 開頭
- **THEN** 系統 SHALL 詢問使用者選擇 MAJOR / MINOR / PATCH，不預設任何建議

---

### Requirement: 版號確認與 tag 建立（Step 5.5）
系統 SHALL 在 merge 完成、分支清理後（Step 5 之後），若偵測到 CHANGELOG 修改，執行版號確認並建立 annotated git tag。

#### Scenario: 使用者確認打 tag
- **WHEN** 使用者在 Step 5.5 確認版號（或接受建議）
- **THEN** 系統 SHALL 執行 `git tag -a <version> -m "<version> — <description>"` 並顯示成功訊息

#### Scenario: 使用者跳過打 tag
- **WHEN** 使用者在 Step 5.5 選擇不打 tag
- **THEN** 系統 SHALL 跳過 tag 建立並在 Step 6 維持原有 push 指令（不加 `--tags`）

#### Scenario: 使用者覆蓋建議版號
- **WHEN** 使用者在 Step 5.5 輸入自訂版號（非建議值）
- **THEN** 系統 SHALL 使用使用者輸入的版號建立 tag，不強制驗證格式（但顯示警告若不符合 SemVer）

---

### Requirement: Push 整合 --tags
系統 SHALL 在使用者選擇打 tag 後，Step 6 的 push 指令自動改為含 `--tags`。

#### Scenario: 有打 tag 時 push 指令含 --tags
- **WHEN** Step 5.5 已成功建立 tag
- **THEN** Step 6 顯示的 push 指令 SHALL 為 `git push origin main --tags`

#### Scenario: 無 tag 時 push 指令維持原樣
- **WHEN** Step 5.5 跳過或未觸發
- **THEN** Step 6 顯示的 push 指令 SHALL 維持 `git push origin main`
