---
name: ctx:experiment
description: 架構實驗工作流。以 git branch 作為隔離容器，提供 start / diff / promote / discard 四個操作。
---

架構實驗工作流。用於「還不確定方案，先試試看」的場景——無需 OpenSpec proposal，實驗結果可 promote 或 discard，記錄永遠保留在 `openspec/experiments/INDEX.md`。

**Input**: `$ARGUMENTS`
- `start <name>` → 建立實驗 branch 並記錄到 INDEX.md
- `diff` → 顯示實驗 branch 相對於 main 的變更摘要
- `promote [conclusion]` → 標記實驗為 promoted，提示執行 `/ctx:merge`
- `discard <conclusion> [--delete]` → 標記為 discarded，checkout main，選擇性刪除 branch

---

## 子操作：`start <name>`

### Step 1 — 邊界檢查

執行：

```bash
git status --short
git branch --show-current
```

如果偵測到 uncommitted changes，**警告使用者**：

```
⚠ 偵測到未 commit 的變更：
  <file list>

繼續開實驗 branch 會帶入這些變更。建議先 commit 或 stash。
要繼續還是暫停？
```

等待確認後再繼續。

### Step 2 — 建立 branch

取今日日期（格式 YYYY-MM-DD），建立 branch：

```bash
git checkout main
git checkout -b experiment/<YYYY-MM-DD>-<name>
```

例如：`/ctx:experiment start test-survey-obs` → branch `experiment/2026-04-06-test-survey-obs`

### Step 3 — 更新 INDEX.md

確認 `openspec/experiments/` 目錄存在（若不存在則建立）。

在 `openspec/experiments/INDEX.md` 的表格尾端 append 一行：

```
| <YYYY-MM-DD> | experiment/<YYYY-MM-DD>-<name> | <name>（purpose 從 name 推導）| in-progress | — |
```

若 INDEX.md 不存在，先建立含標頭與空表格的初始檔案，再 append。

### Step 4 — 顯示說明

```
✓ 實驗 branch 已建立：experiment/<YYYY-MM-DD>-<name>
✓ INDEX.md 已更新

接下來可以手動執行 observer/reflector：
  uv run python infra/periodic_jobs/ai_heartbeat/src/v0/observer.py
  uv run python infra/periodic_jobs/ai_heartbeat/src/v0/reflector.py

⚠ 注意：reflector 會消費 OBSERVATIONS.md（GC 刪除條目）。
  若要比較兩種 reflector 策略，請開兩個獨立 branch，不能在同一 branch 重跑。

完成後執行 /ctx:experiment diff 檢視變更。
```

---

## 子操作：`diff`

### Step 1 — 邊界檢查

執行：

```bash
git branch --show-current
```

如果當前 branch 不以 `experiment/` 開頭，**警告並提示**：

```
⚠ 當前分支不是 experiment branch：<current-branch>
  diff 操作設計用於 experiment/ 分支。

要繼續還是切換到正確的 experiment branch？
```

### Step 2 — 執行 diff

```bash
git diff main...HEAD -- memory/OBSERVATIONS.md
git diff main...HEAD -- rules/
git diff main...HEAD --stat
```

### Step 3 — 格式化輸出

```
## 實驗變更摘要

**Branch:** experiment/<name>
**對比基準:** main

### OBSERVATIONS.md 變更
<顯示新增的觀測條目，若無變更則顯示「無變更」>

### rules/ 變更
<列出有修改的 rules/ 檔案清單，若無變更則顯示「無變更」>

### 整體統計
<git diff --stat 輸出>
```

如果完全沒有變更：

```
目前尚無變更（自 branch 建立後未執行 observer/reflector）。
```

---

## 子操作：`promote [conclusion]`

### Step 1 — 邊界檢查

執行：

```bash
git branch --show-current
```

如果當前 branch 不以 `experiment/` 開頭，**警告並停止**：

```
⚠ 當前分支不是 experiment branch：<current-branch>
  promote 操作只能在 experiment/ 分支上執行。
```

### Step 2 — 取得結論

如果 `$ARGUMENTS` 包含 conclusion 文字，使用它。否則詢問：

```
這次實驗的結論是什麼？（會記錄到 INDEX.md）
```

### Step 3 — 更新 INDEX.md

在 `openspec/experiments/INDEX.md` 找到當前 branch 對應的行，更新：
- `status` → `promoted`
- `conclusion` → 填入結論文字

### Step 4 — 顯示提示

```
✓ INDEX.md 已更新：status → promoted
  結論：<conclusion>

下一步：執行 /ctx:merge 將此實驗合併回 main
```

**不自動執行 merge。**

---

## 子操作：`discard <conclusion> [--delete]`

### Step 1 — 邊界檢查

執行：

```bash
git branch --show-current
```

如果當前 branch 不以 `experiment/` 開頭，**警告並停止**：

```
⚠ 當前分支不是 experiment branch：<current-branch>
  discard 操作只能在 experiment/ 分支上執行。
```

### Step 2 — 強制要求 conclusion

`conclusion` 為必填參數（非空字串）。如果未提供或為空，**停止並提示**：

```
✗ 必須提供 conclusion 說明 discard 原因。

用法：/ctx:experiment discard "原因描述" [--delete]
```

### Step 3 — 更新 INDEX.md

在 `openspec/experiments/INDEX.md` 找到當前 branch 對應的行，更新：
- `status` → `discarded`
- `conclusion` → 填入結論文字

commit 此變更（message：`chore: discard experiment <branch-name>`）。

### Step 4 — Checkout main

```bash
git checkout main
```

### Step 5 — 選擇性刪除 branch

**預設**（未帶 `--delete`）：保留 branch，顯示：

```
✓ INDEX.md 已更新：status → discarded
✓ 已切換回 main
  Branch 已保留：experiment/<name>（可之後手動 git branch -D 刪除）
```

**帶 `--delete` flag**：

```bash
git branch -D experiment/<name>
```

顯示：

```
✓ INDEX.md 已更新：status → discarded
✓ 已切換回 main
✓ Branch 已刪除：experiment/<name>
```

---

## Guardrails

- `start` 遇到 uncommitted changes 要警告，不自動 stash
- `diff`、`promote`、`discard` 在非 experiment branch 上執行時必須警告
- `discard` 的 conclusion 為必填，不允許空字串
- `promote` 不執行 merge，只更新 INDEX.md 並提示 `/ctx:merge`
- INDEX.md 不存在時自動初始化（標頭 + 空表格），再 append
- 不修改 `observer.py` / `reflector.py`，實驗執行由使用者手動操作
