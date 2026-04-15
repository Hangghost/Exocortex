# Spec: ctx:merge Command (Delta)

## ADDED Requirements

### Requirement: content/ branch 合併時跳過架構文件審查
ctx:merge 在合併 `content/YYYY-MM-DD` branch 時 SHALL 跳過 Step 2 的架構文件審查（WORKSPACE.md、AGENTS.md 等），直接進入 Step 3 確認合併。

#### Scenario: 合併 content/ branch 偵測
- **WHEN** 當前 branch 名稱符合 `content/YYYY-MM-DD` 格式
- **THEN** ctx:merge SHALL 標記本次為「content merge」，跳過 Step 2 架構文件審查

#### Scenario: content merge 的 Step 2 替代顯示
- **WHEN** content merge 跳過文件審查
- **THEN** 系統 SHALL 顯示「content branch 合併，跳過架構文件審查」並直接進入 Step 3

#### Scenario: 非 content branch 審查不受影響
- **WHEN** 當前 branch 名稱符合 `feature/*` 或其他非 content/ 格式
- **THEN** ctx:merge SHALL 維持原有 Step 2 架構文件審查流程，不受影響

---

## MODIFIED Requirements

### Requirement: Step 2 文件審查包含 CHANGELOG 版號偵測
ctx:merge 的 Step 2（文件審查）SHALL 在現有 diff 掃描基礎上，額外偵測 CHANGELOG.md 是否被修改，並於審查結果中顯示偵測狀態。

#### Scenario: CHANGELOG 有修改時顯示版號預告
- **WHEN** diff 掃描偵測到 `CHANGELOG.md` 在變動清單中
- **THEN** Step 2 審查結果 SHALL 新增一行：`⚑ 偵測到 CHANGELOG.md 更新，版號：X.Y.Z — 描述（合併後於 Step 5.5 確認 tag）`

#### Scenario: CHANGELOG 無修改時審查結果不變
- **WHEN** diff 掃描未偵測到 CHANGELOG.md 修改
- **THEN** Step 2 審查結果 SHALL 維持原有格式，不顯示任何版號相關資訊

---

### Requirement: Step 5.5 版號 tag 確認（新增步驟）
ctx:merge SHALL 在 Step 5（清理分支）之後、Step 6（Push）之前，插入 Step 5.5 版號確認步驟。此步驟僅在 Step 2 偵測到 CHANGELOG 修改時出現。

#### Scenario: 詢問格式
- **WHEN** Step 5.5 觸發
- **THEN** 系統 SHALL 顯示：
  ```
  ⚑ 偵測到 CHANGELOG.md 更新（branch: <branch-name>）
    版號：<X.Y.Z> — <描述>
    建議 bump 類型：<MINOR/PATCH>（依 branch 前綴推斷）
    建議新版號：<X.Y+1.0  或 X.Y.Z+1>

    確認打 tag <version>？[Y/n] 或輸入自訂版號：
  ```

#### Scenario: 確認後執行 tag
- **WHEN** 使用者按 Enter 或輸入 y
- **THEN** 系統 SHALL 執行 `git tag -a <version> -m "<version> — <description>"` 並顯示 `✓ 已建立 tag: <version>`

---

### Requirement: Step 6 push 指令依 tag 狀態調整
ctx:merge 的 Step 6 SHALL 依照是否建立了 tag，動態調整顯示的 push 指令。

#### Scenario: 有 tag 時顯示 --tags
- **WHEN** Step 5.5 已建立 tag
- **THEN** Step 6 顯示的 push 指令 SHALL 為 `git push origin main --tags`

#### Scenario: 無 tag 時維持原樣
- **WHEN** Step 5.5 未建立 tag 或未觸發
- **THEN** Step 6 顯示的 push 指令 SHALL 維持 `git push origin main`
