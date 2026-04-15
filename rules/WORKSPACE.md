# WORKSPACE.md - 目錄路由速查

目標：讓 AI 每輪 session 都能快速知道"去哪裡找/放什麼"。**找任何檔案前先查這裡。**

> **設計新功能或進行架構變更前**，先讀 `rules/ARCHITECTURE.md`——了解各區塊設計意圖、邊界與資料流，再開始規劃。

## 路由規則

### 專案與程式碼
- 寫程式碼 / 跑指令碼 / 一次性專案：`infra/adhoc_jobs/<project>/`
- 工具指令碼（郵件、語義搜尋、分享報告等）：`infra/tools/`
- 定時任務：`infra/periodic_jobs/`

### 知識與記錄
- 通用研究報告：`contexts/survey_sessions/`
- 思考 / 覆盤 / 方法論：`contexts/thought_review/`
- 部落格文章草稿與思考產物：`contexts/blog/`
- 工作紀錄（任務執行過程、進度、產出）：`contexts/work_logs/`
- `contexts/` 子資料夾的觀察設定 → `contexts/MANIFEST.md`
- 系統記憶（observer/reflector 產出）：`memory/`
- 快速捕獲（待辦、閱讀清單、靈感、raw notes）：`inbox/`
- **域知識查詢**（技術文章、論文、外部概念）：`registry/knowledge.md` → `~/Documents/Procjects/KnowledgeWiki/INDEX.md`
  - 查詢路徑：`registry/knowledge.md` → `KnowledgeWiki/INDEX.md` → `concepts/<topic>.md`
  - KnowledgeWiki 為獨立 repo，與 Exocortex 平行存在；`contexts/` 只存個人行為記錄
- **領域路由索引**（跨系統任務時查詢）：`registry/`
  - `registry/career.md` — 履歷、工作記錄、專案經歷、技術能力的資訊來源
  - `registry/dev.md` — 活躍 repo、開發筆記、Jira issue tracking 的資訊來源
  - `registry/life.md` — 目標、學習計畫、待辦事項的資訊來源
- **專案脈絡**：`projects/`
  - `projects/INDEX.md`：所有專案一覽（被動載入，取代舊有的 `state/active.md`）
  - `projects/<name>/PROJECT.md`：單一專案的目標、現況、下一步、決策、材料地圖——用 `/ctx:project load <name>` 載入
  - `projects/<name>/context/`：深度技術文件（按需，不自動載入）

### 個人 Library

- **個人珍藏文件索引**（文章、PDF、個人文件）：`registry/library.md` → `library/INDEX.md` → `library/<card>.md`
  - Index cards 在 repo，binary 本體放 `~/Documents/AILibrary/`，AI 透過 card 的 `file_path` 定位
  - 格式規範見 `library/README.md`

### 系統與規則
- **跨 agent 共享行為協定（SSOT）**：`rules/CORE.md` — 所有 agent 每 session 必讀，包含 session 閱讀清單、記憶架構、sub-agent 路由、Opus 模式、safety
- 系統 Skills（跨 agent 可複用能力）：`rules/skills/`
- 核心公理（Axioms）：`rules/axioms/`
- 環境事實（設備、帳號、工具）：`rules/ENVIRONMENT.md`
- 記憶系統：`memory/` + `infra/periodic_jobs/ai_heartbeat/`

### Git Hook

換機後需重裝 pre-commit hook（防止 AGENTS.md / CLAUDE.md 與 CORE.md drift）：

```bash
cp .git-hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

### 設計工作流
- 架構變更提案、設計文件、任務清單：`openspec/changes/<change-name>/`
- 已歸檔的變更：`openspec/changes/archive/`
- 主規格（已同步的能力 spec）：`openspec/specs/<capability>/spec.md`
  - 注意：`openspec/changes/<name>/specs/` 是草稿，apply 任務之一是同步進 `openspec/specs/`
- 系統演進里程碑記錄：`CHANGELOG.md`（根目錄，以里程碑為單位分組已歸檔的 changes）
- 架構實驗記錄索引：`openspec/experiments/INDEX.md`（每次 `ctx:experiment start/promote/discard` 自動更新）

### Claude Commands 位置
- **project-scoped**：`<project-root>/.claude/commands/`（需在該 repo 根目錄）
- **user-scoped**：`~/.claude/commands/`（全局可用，跨所有 repo）
- 兩者不同位置，安裝 OpenSpec 或新增 slash commands 時需確認目標範疇

### 參考素材（隔離區）
- `_reference/`：非架構、待消化的參考素材，AI 不主動載入。包含前任使用者的公理、playbook、工具腳本與排程任務，僅供人工查閱。

## 命名規則
- 目錄和檔名：小寫 + 下劃線 (snake_case)
- 臨時一次性專案：`tmp_<name>/`

## Python 環境
- 依賴定義於根目錄 `pyproject.toml`，用 `uv sync --all-groups` 安裝
- 每個 skill 的依賴有獨立 group（如 `obsidian`）；新增 skill 依賴時在 `pyproject.toml` 新增 group
- 需要隔離時在 `infra/adhoc_jobs/<project>/.venv/` 建獨立環境

## 快速查詢

<!-- 隨著你的專案增長，在這裡新增活躍專案的快捷路由 -->
<!-- 格式：- `project-name` → `adhoc_jobs/project_name/` (說明) -->
