---
name: ctx:content
description: 內容提交工作流。掃描內容層、確認邊界、開分支（可選）、commit。支援 `merge` 子命令合併今天的 content branch。
---

內容提交工作流。用於提交任務產出：survey sessions、work logs、OBSERVATIONS.md 更新、infra/adhoc_jobs 等。

**Input**: `$ARGUMENTS`
- 空白 → 自動掃描並列出所有待提交內容
- 任務描述（例如 `研究 claude-code 架構`）→ 作為 commit message 的語意 hint
- `merge` → 合併今天的 content/YYYY-MM-DD branch 到 main（見下方 merge 子命令）

---

## merge 子命令

**觸發條件**：`$ARGUMENTS` 為 `merge`，執行此區塊，完成後結束，不執行後續 Step 1–5。

End-of-day 輕量合併，跳過架構文件審查。

### merge Step 1 — 確認 content branch 存在

執行：

```bash
git branch --list "content/$(date +%Y-%m-%d)"
```

- 若 `content/YYYY-MM-DD` **不存在**：顯示「今天尚無 content/YYYY-MM-DD 分支」並結束，不執行任何 git 操作。

### merge Step 2 — 若有未提交內容，先 commit

執行：

```bash
git status --short
```

若偵測到任何未提交的內容層檔案（`contexts/`、`memory/`、`inbox/`、`infra/` 等），先切換至 `content/YYYY-MM-DD`，觸發預設 commit 流程（Step 1–5），完成後繼續 merge。

### merge Step 3 — 顯示 commit 列表並確認

執行：

```bash
git log main..content/YYYY-MM-DD --oneline
```

顯示：

```
準備合併 content/YYYY-MM-DD → main

Commits：
  abc1234 content: add survey on ...
  def5678 mem: update observations

確認合併？[Enter]
```

### merge Step 4 — 執行合併與清理

```bash
git checkout main
git merge --no-ff content/YYYY-MM-DD -m "Merge content/YYYY-MM-DD"
git branch -d content/YYYY-MM-DD
```

### merge Step 5 — 完成訊息

```
✓ 已合併 content/YYYY-MM-DD → main。
若要 push：git push origin main

（架構 branch 請用 /ctx:merge）
```

---

## Step 1 — 互斥檢查

執行：

```bash
git status --short
```

如果偵測到以下架構層檔案有未 commit 的變更，**中斷並提示**：

- `rules/` 下任何檔案
- `AGENTS.md`
- `CLAUDE.md`

提示訊息：
```
偵測到架構層檔案有未提交的變更：
  M rules/WORKSPACE.md

建議先用 /ctx:arch 處理架構變更，再提交內容。
要繼續還是先暫停？
```

如果使用者選擇繼續，則將架構檔案排除在本次 commit 之外，繼續執行。

---

## Step 2 — 掃描並分組

列出所有 untracked 和 modified 的**內容層**檔案，按類型分組：

```
## 待提交內容

**Blog Posts**（部落格草稿與思考產物）
- contexts/blog/2026-04-01_some-article.md

**Survey Sessions**（研究報告）
- contexts/survey_sessions/2026-04-01_claude-code-src-insight.md
- contexts/survey_sessions/http-payload-encryption-discussion.md

**Work Logs**（工作紀錄）
- contexts/work_logs/...

**動態記憶**
- memory/OBSERVATIONS.md

**Periodic Jobs**（腳本/文件）
- infra/periodic_jobs/ai_heartbeat/src/v0/observer.py
- infra/periodic_jobs/ai_heartbeat/docs/KNOWLEDGE_BASE.md

**Adhoc Projects**
- infra/adhoc_jobs/WWPF_API/
- infra/adhoc_jobs/qtm-api-1.48.0/
```

---

## Step 3 — 分支決策

執行：

```bash
git branch --show-current
```

根據當前分支類型，決定目標分支：

### 已在 `content/*` 分支

直接在當前 `content/YYYY-MM-DD` 分支 commit，不做切換。

### 在 `main` 分支

建立或切換至今天的 content branch：

- 若 `content/YYYY-MM-DD` **不存在**：
  ```bash
  git checkout main
  git checkout -b content/YYYY-MM-DD
  ```
- 若 `content/YYYY-MM-DD` **已存在**：
  ```bash
  git checkout content/YYYY-MM-DD
  ```

### 在 `feature/*` 分支

自動重定向，顯示：「偵測到目前在 feature/X，content 將提交到 content/YYYY-MM-DD」

然後：

1. 若 `content/YYYY-MM-DD` **不存在**：
   ```bash
   git checkout main
   git checkout -b content/YYYY-MM-DD
   ```
2. 若 `content/YYYY-MM-DD` **已存在**：
   ```bash
   git checkout content/YYYY-MM-DD
   ```
3. 執行 Step 4–5 commit 流程
4. commit 完成後切回原 feature branch：
   ```bash
   git checkout feature/X
   ```
5. 顯示：「已提交至 content/YYYY-MM-DD，已切回 feature/X」

---

## Step 4 — 確認並提交

根據本次內容自動產生語意化的 commit message：

格式規則：
- 新增 survey session → `docs: add survey on <主題>`
- 更新 OBSERVATIONS.md → `mem: update observations - <關鍵變化>`
- 新增 work log → `logs: add work log for <任務>`
- Adhoc 專案 → `adhoc: add <project-name>`
- 混合內容 → `content: <本次最主要的主題>`

如果使用者提供了 `$ARGUMENTS`，優先使用它作為主題描述，不再詢問。

顯示單一確認畫面，等待 Enter 後執行：

```
待提交：
  📁 Survey Sessions  contexts/survey_sessions/2026-04-01_claude.md
  📁 動態記憶        memory/OBSERVATIONS.md

分支：content/YYYY-MM-DD
Commit：docs: add survey on claude-code architecture

確認？[Enter]
```

確認後執行：

```bash
git add <選定的檔案>
git commit -m "..."
```

完成後顯示 commit SHA 和包含的檔案清單。

---

## Guardrails

- 永遠不要在本 skill 中 stage `rules/`、`AGENTS.md`、`CLAUDE.md`
- 如果使用者選擇全排除（沒有東西要 commit），直接結束，不執行 commit
- commit message 用中文或英文跟隨現有 repo 風格（檢查最近幾筆 `git log --oneline -5`）
- `content/YYYY-MM-DD` 永遠從 main 建立，不從 feature/* 建立
