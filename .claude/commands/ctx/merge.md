---
name: ctx:merge
description: 合併 feature branch 回 main，清理分支。架構流程與內容流程共用的終止操作。
---

合併 feature branch 回 main，清理分支。這是架構流程（opsx → ctx:arch）與內容流程（ctx:content）共用的最後一步。

**Input**: `$ARGUMENTS`
- 空白 → 自動偵測當前分支並執行，完成後顯示 push 指令但不執行
- branch name → 指定要合併的分支
- `--push` → 合併後自動接續 push（Bash 確認視窗為唯一安全門）

---

## Step 1 — 確認當前狀態

執行：

```bash
git branch --show-current
git status --short
git log main..HEAD --oneline
git diff main...HEAD --name-only
```

顯示：
- 當前分支名稱
- 是否有未 commit 的變更
- 相對於 main 的 commit 列表

如果有未 commit 的變更，**中斷並提示**，同時分析哪些變更屬於這個分支：

根據分支名稱、已有 commit 的檔案路徑模式（`git diff main...HEAD --name-only` 的結果），對 `git status --short` 列出的每個未 commit 檔案進行判斷：

- **屬於此分支**：檔案路徑或類型與本分支的已 commit 變更一致，或與分支名稱暗示的範圍相符
- **可能不屬於此分支**：檔案路徑或類型與本分支範圍無關，或看起來是其他功能/修復的一部分

顯示格式：

```
還有未提交的變更，建議先完成 commit 再合併。

未提交檔案分析（分支：<branch-name>）：
  ✓ path/to/file-a.md       — 屬於此分支（與已 commit 的變更範圍一致）
  ✓ path/to/file-b.py       — 屬於此分支（分支名稱範圍相符）
  ⚠ path/to/unrelated.md   — 可能不屬於此分支（與本分支範圍無關）

建議：先將屬於此分支的變更 commit，不屬於的移至其他分支或暫存（git stash）。
要繼續強制合併還是先暫停？
```

---

## Step 2 — 文件審查（pre-merge doc review）

**content branch 偵測**：若當前分支名稱符合 `content/YYYY-MM-DD` 格式（`content/\d{4}-\d{2}-\d{2}`），標記為「content merge」，顯示：

```
content branch 合併，跳過架構文件審查
```

然後直接跳至 Step 3，不執行以下文件審查。

---

執行 diff 掃描，列出這次分支的所有變動：

```bash
git diff main...HEAD --name-only
git diff main...HEAD --stat
```

逐項檢查，判斷是否需要更新文件：

| 變動類型 | 需要審查的文件 |
|---|---|
| 新增資料夾 | `rules/WORKSPACE.md`（file routing index）、`AGENTS.md`（如有新工具或指令）|
| 新增或修改 skill/command | `.claude/commands/` 或 `.claude/skills/` 對應的 SKILL.md、`AGENTS.md` skill index |
| 修改架構或規則 | `rules/` 相關檔案、`CLAUDE.md` |
| 新增 registry 項目 | `registry/` 對應的 `.md` |
| 修改 periodic jobs | `infra/periodic_jobs/CRONTAB.md`、`infra/periodic_jobs/ai_heartbeat/docs/KNOWLEDGE_BASE.md` |
| **新增/刪除頂層目錄，或改變資料流向** | `rules/ARCHITECTURE.md`（架構地圖）|

額外掃描：執行 `git diff main...HEAD --name-only | grep CHANGELOG.md`

若 CHANGELOG.md 在變動清單中，解析最新版號條目（格式 `## X.Y.Z — 描述`），顯示於審查結果中：

```
⚑ 偵測到 CHANGELOG.md 更新，版號：X.Y.Z — 描述
  （合併後於 Step 5.5 確認是否打 git tag）
```

記住此版號與描述，供 Step 5.5 使用。若無法解析出符合 `\d+\.\d+\.\d+` 格式的版號，記錄「需手動輸入版號」。

顯示審查結果：

```
## 文件審查結果

變動摘要：
  - 新增：path/to/new-folder/
  - 修改：path/to/changed-file.md

需要更新：
  ✗ rules/WORKSPACE.md — 新資料夾未列入 routing index
  ✓ AGENTS.md — 無需更新

建議動作：
  1. 更新 rules/WORKSPACE.md，加入 new-folder/ 的路由說明
```

如果有需要更新的文件，**先執行更新並 commit，再繼續 Step 3**。

如果無需更新，直接進入 Step 3。

---

## Step 3 — 確認合併

顯示摘要：

```
## 準備合併

**分支：** feature/add-work-logs-routing
**目標：** main
**Commits：**
  abc1234 feat: add work logs routing to WORKSPACE.md
  def5678 docs: update AGENTS.md skill index

確認合併？
```

---

## Step 4 — 執行合併

```bash
git checkout main
git merge --no-ff <branch-name> -m "Merge <branch-name>"
```

使用 `--no-ff` 保留分支歷史。

---

## Step 5 — 清理分支

```bash
git branch -d <branch-name>
```

顯示完成訊息：

```
✓ 已合併：feature/add-work-logs-routing → main
✓ 已刪除分支：feature/add-work-logs-routing

Merge commit: <SHA>
```

---

## Step 5.5 — 版號 Tag（僅在 CHANGELOG 有變動時出現）

若 Step 2 偵測到 CHANGELOG.md 修改，在此步驟詢問是否建立 git tag。

依 branch 名稱前綴推斷建議 bump 類型：
- `feature/*` → MINOR bump（X.Y.0 → X.Y+1.0）
- `fix/*` → PATCH bump（X.Y.Z → X.Y.Z+1）
- 其他前綴 → 詢問使用者選擇 MAJOR / MINOR / PATCH

顯示確認訊息：

```
⚑ 偵測到 CHANGELOG.md 更新（branch: <branch-name>）
  版號：<X.Y.Z> — <描述>
  建議 bump 類型：<MINOR/PATCH>（依 branch 前綴推斷）
  建議新版號：<X.Y+1.0 或 X.Y.Z+1>

  確認打 tag <version>？[Y/n] 或輸入自訂版號：
```

- 若確認（Enter 或 `y`）：執行 `git tag -a <version> -m "<version> — <描述>"`，顯示 `✓ 已建立 tag: <version>`
- 若跳過（`n`）：不建立 tag，Step 6 維持原有 push 指令
- 若輸入自訂版號：使用自訂版號，若不符合 SemVer 格式則顯示警告但不阻止

---

## Step 6 — Push 到 Remote

**預設行為**（未帶 `--push`）：

顯示完成訊息後，只印出指令供使用者自行決定時機：

- 若 Step 5.5 **有建立 tag**：

```
若要 push 到 remote，執行：

  git push origin main --tags
```

- 若 Step 5.5 **未建立 tag**（或未觸發）：

```
若要 push 到 remote，執行：

  git push origin main
```

**帶 `--push` flag**：

直接執行（Bash 確認視窗為唯一安全門）：

- 若 Step 5.5 有建立 tag：`git push origin main --tags`
- 否則：`git push origin main`

---

## Guardrails

- 永遠使用 `--no-ff`，保留分支歷史
- 如果有 conflict，中斷並提示使用者手動解決，不自動解
- 不強制 push（不用 `--force`）
- 如果已在 main 分支，直接提示「已在 main，無需合併」並結束
