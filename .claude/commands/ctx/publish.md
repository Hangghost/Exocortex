---
name: ctx:publish
description: 將 private repo 的架構變更發布到 public template repo（Exocortex）。以 openspec change 為單位，依 taxonomy 判斷檔案處理策略，產出 PUBLISH PLAN 供人審閱，確認後執行 apply 並建立 published.md marker。
---

將 private `exocortex-personal` 的架構變更發布到 public `Exocortex` template repo（local clone: `~/Documents/Projects/Exocortex/`）。

**Input**: `$ARGUMENTS`
- 空白 → 掃描所有未 publish 的 archived changes，供使用者選擇
- change name → 直接指定要 publish 的 change（可指定多個，空格分隔）

---

## 檔案分類 Taxonomy

所有待 publish 的檔案依以下規則分類：

| 類型 | 策略 | Patterns |
|------|------|---------|
| `pure-arch` | **copy verbatim** — 直接複製到 template | `.claude/skills/**`, `rules/skills/**`, `infra/tools/**`, `infra/periodic_jobs/**` |
| `structural` | **AI semantic merge** — 讀 private diff + template 現有版本 + proposal 意圖，產出 merged content | `CLAUDE.md`, `rules/CORE.md`, `rules/WORKSPACE.md`, `rules/ARCHITECTURE.md`, `rules/COMMUNICATION.md`, `.gitignore`, `pyproject.toml` |
| `personal-struct` | **skip** — template 已有 placeholder，不覆蓋 | `rules/USER.md`, `rules/ENVIRONMENT.md`, `rules/SOUL.md`, `registry/**`, `inbox/**` |
| `never` | **skip** — 純個人內容，絕不發布 | `openspec/changes/**`, `memory/**`, `contexts/**`, `projects/**`, `library/**` |

任何未匹配上述 pattern 的檔案，AI 依語義判斷歸類，並在 PUBLISH PLAN 中標明判斷理由。

---

## Step 1 — 掃描未 publish Changes

```bash
ls ~/Documents/Projects/Exocortex-personal/openspec/changes/archive/
```

對每個 archive entry，檢查是否存在 `published.md`：

```bash
ls openspec/changes/archive/*/published.md 2>/dev/null
```

**若所有 archive entries 都已有 `published.md`**：

```
所有 archived changes 都已發布到 template。無待發布項目。
```

然後結束。

**否則**，列出未 publish 的 changes，讓使用者選擇（或若 `$ARGUMENTS` 已指定則跳過此步驟）：

```
## 未發布的 Changes

1. ctx-publish — [change 簡介，從 proposal.md 的 Why 提取一行]
2. another-change — [簡介]

請選擇要發布的 changes（輸入編號，多個用空格，或 all）：
```

---

## Step 2 — 讀取 Change 內容

對每個選定的 change，讀取：
- `openspec/changes/archive/<name>/tasks.md`：了解哪些檔案被修改
- `openspec/changes/archive/<name>/proposal.md`：了解變更意圖
- 若存在：`openspec/changes/archive/<name>/design.md`

從 `tasks.md` 提取所有 `[x]` 完成的任務，解析其中涉及的檔案路徑。

---

## Step 3 — 前置同步 Template Clone

```bash
cd ~/Documents/Projects/Exocortex/ && git pull
```

若有衝突或錯誤，顯示錯誤訊息並中斷，提示使用者手動解決後重新執行。

---

## Step 4 — 產出 PUBLISH PLAN

依 taxonomy 對每個檔案分類，然後產出完整 PUBLISH PLAN：

```
## PUBLISH PLAN

**Changes included:** ctx-publish[, ...]
**Template target:** ~/Documents/Projects/Exocortex/

---

### COPY（pure-arch，直接複製）

| 檔案 | 操作 |
|------|------|
| .claude/skills/foo/SKILL.md | copy |
| rules/skills/bar/SKILL.md | copy |

---

### MERGE PREVIEW（structural，AI 語義合併）

#### CLAUDE.md

```diff
[展示 proposed merged content，標記新增/移除的段落]
```

#### rules/WORKSPACE.md

```diff
[展示 proposed merged content]
```

---

### SKIP

| 檔案 | 原因 |
|------|------|
| rules/USER.md | personal-struct — template 有 placeholder |
| openspec/changes/ctx-publish/ | never — openspec 歷史不發布 |
| memory/** | never — 純個人記憶 |

---

確認此 PUBLISH PLAN 並執行？[Y/n/edit]
```

**Structural 檔案 semantic merge 方法**：
1. 取得 private 的 git diff：`git diff main -- <file>` 或比較 archive 前後
2. 讀取 template 目前版本：`cat ~/Documents/Projects/Exocortex/<file>`
3. 讀取 proposal.md 的意圖說明
4. 產出 merged content 規則：
   - 保留 template 版本中的「使用者填寫」TODO placeholder
   - 只加入架構性的新增內容（新 routing、新 requirement、新設計原則）
   - 移除或替換任何含個人路徑、帳號名稱、設備名的內容

---

## Step 5 — 使用者確認

- **使用者確認**（Enter 或 `y`）：繼續執行 Step 6
- **使用者拒絕**（`n`）：停止，不執行任何操作，顯示「已取消，PUBLISH PLAN 未 apply。」
- **使用者要求修改**（`edit`）：展示每個 structural 檔案的 proposed content，讓使用者指出需要調整的部分，重新產出後回到本步驟

---

## Step 6 — Apply

### 6.1 Apply COPY 操作

對每個 pure-arch 檔案：

```bash
# 確保目標目錄存在
mkdir -p ~/Documents/Projects/Exocortex/$(dirname <file>)
# 複製
cp /Users/dj_workstation/Documents/Projects/Exocortex-personal/<file> \
   ~/Documents/Projects/Exocortex/<file>
```

### 6.2 Apply MERGE 操作

對每個 structural 檔案，將 Step 4 產出的 merged content 寫入 template clone：

```bash
# 寫入 merged content 到 template
cat > ~/Documents/Projects/Exocortex/<file> << 'EOF'
<merged content>
EOF
```

### 6.3 Commit Template Clone

```bash
cd ~/Documents/Projects/Exocortex/
git add -A
git commit -m "publish: <change-name(s)> — <一行描述來自 proposal Why>"
```

記錄 commit hash（供 published.md 使用）：

```bash
git rev-parse HEAD
```

---

## Step 7 — 建立 Published Marker

對每個已 publish 的 change，在其 archive 目錄建立 `published.md`：

```markdown
---
published_at: YYYY-MM-DD
template_commit: <commit-hash>
changes_included:
  - <change-name>
---
```

建立於 `openspec/changes/archive/<change-name>/published.md`。

若為多個 changes 批次 publish，每個 change 各自建立 marker，`changes_included` 列出本次批次所有 change names。

---

## Step 8 — Commit Private Repo Marker

```bash
git add openspec/changes/archive/*/published.md
git commit -m "publish: mark <change-name(s)> as published to template"
```

---

## Step 9 — 完成報告

```
## Publish 完成

**Changes published:** ctx-publish[, ...]
**Template commit:** <hash>
**Template target:** ~/Documents/Projects/Exocortex/

已建立 published.md markers：
  ✓ openspec/changes/archive/ctx-publish/published.md

若要 push template 到 remote，切換到 template clone 執行：
  cd ~/Documents/Projects/Exocortex/ && git push origin main
```

---

## Guardrails

- **不自動 push**：commit 後由人決定何時 push（template 和 private 都不自動 push）
- **Apply 前必須確認**：PUBLISH PLAN 未確認前不執行任何寫入操作
- **個人資料隔離**：structural merge 時主動檢查 output 中是否含有個人路徑、帳號名、設備名，若有則標記警告並要求人工確認
- **Template pull 先行**：Step 3 失敗（有衝突）時中斷，不繼續
- **Marker 是 post-commit 操作**：只有 template commit 成功後才建立 published.md
