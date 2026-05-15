# WORKSPACE.md - 目錄路由速查

目標：讓 AI 每輪 session 都能快速知道"去哪裡找/放什麼"。**找任何檔案前先查這裡。**

> **設計新功能或進行架構變更前**，先讀 `rules/ARCHITECTURE.md`——了解各區塊設計意圖、邊界與資料流，再開始規劃。

## 路由規則

### 專案與程式碼
- 寫程式碼 / 跑指令碼 / 一次性專案：`infra/adhoc_jobs/<project>/`
- 工具指令碼（郵件、語義搜尋等）：`infra/tools/`
- 定時任務：`infra/periodic_jobs/`
- 系統執行狀態（system_state.json + helper）：`infra/state/`

### 知識與記錄
- 通用研究報告：`contexts/survey_sessions/`
- 思考 / 覆盤 / 方法論：`contexts/thought_review/`
- 部落格文章草稿與思考產物：`contexts/blog/`
- 工作紀錄（任務執行過程、進度、產出）：`contexts/work_logs/`
- `contexts/` 子資料夾的觀察設定 → `contexts/MANIFEST.md`
- 系統記憶（observer/reflector 產出）：`memory/`
- 快速捕獲（待辦、閱讀清單、靈感、raw notes）：`inbox/`
- **領域路由索引**（跨系統任務時查詢）：`registry/`
  - `registry/career.md` — 履歷、工作記錄、專案經歷、技術能力的資訊來源
  - `registry/dev.md` — 活躍 repo、開發筆記、issue tracking 的資訊來源
  - `registry/life.md` — 目標、學習計畫、待辦事項的資訊來源
- **專案脈絡**：`projects/`
  - `projects/INDEX.md`：所有專案一覽（被動載入）
  - `projects/<name>/PROJECT.md`：單一專案的目標、現況、下一步、決策、材料地圖——用 `/ctx:project load <name>` 載入
  - `projects/<name>/context/`：深度技術文件（按需，不自動載入）

### 個人 Library（選用）

- **個人珍藏文件索引**（文章、PDF、個人文件）：`registry/library.md` → `library/INDEX.md` → `library/<card>.md`
  - Index cards 在 repo，binary 本體放在你自己的 local 文件目錄（不入 git），AI 透過 card 的 `file_path` 定位
  - 格式規範見 `library/README.md`

### 系統與規則
- **跨 agent 共享行為協定（SSOT）**：`rules/CORE.md` — 所有 agent 每 session 必讀，包含 session 閱讀清單、記憶架構、sub-agent 路由、safety
- 系統 Skills（**作用對象在此 repo 內部**、跨 agent 可複用）：`rules/skills/`
- 核心公理（Axioms）：`rules/axioms/`
- 環境事實（設備、帳號、工具）：`rules/ENVIRONMENT.md`
- 記憶系統：`memory/` + `infra/periodic_jobs/ai_heartbeat/`

### Git Hook

換機後需重裝 pre-commit hook（防止 AGENTS.md / CLAUDE.md 與 CORE.md drift）：

```bash
cp .git-hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

### 分支命名約定

本 repo 工作分支限定三類，各有明確資料範疇與生命週期。任何 skill/command 偵測分支類型時，以 `/` 前綴判定，未知前綴詢問使用者。

| Pattern | 生命週期 | 資料範疇 | 合併策略 |
|---|---|---|---|
| `content/YYYY-MM-DD` | short-lived（一日） | `contexts/`、`memory/`、`inbox/` 等 event-shaped | `--squash`（單一 daily snapshot commit） |
| `project/<name>` | long-lived（專案 create→complete） | `projects/<name>/` state-shaped 變更 | `--no-ff`（保留 milestone DAG，分支續命） |
| `feature/<change-name>` | short-lived（一個 openspec change） | `rules/`、`.claude/`、`openspec/` 等架構層 | `--no-ff`（用 `/ctx:merge`） |

**關鍵原則**：
- `project/<name>` 從專案 `create` 建立到 `complete` 才刪，期間 milestone merge 後分支續命；不自動 rebase 或 merge main（避免 SHA 改寫破壞多機同步）
- `projects/INDEX.md` 中 `status: active|paused` 的專案 ≡ 活躍的 `project/*` 分支（SSOT）
- 混合變更（同時動到 `contexts/` + `projects/<X>/`）由 `/ctx:content` 自動拆兩個 commit 分送
- 細節見 `openspec/specs/project-branch-flow/spec.md`

### 設計工作流
- 架構變更提案、設計文件、任務清單：`openspec/changes/<change-name>/`
- 已歸檔的變更：`openspec/changes/archive/`
- 主規格（已同步的能力 spec）：`openspec/specs/<capability>/spec.md`
  - 注意：`openspec/changes/<name>/specs/` 是草稿，apply 任務之一是同步進 `openspec/specs/`
- 系統演進里程碑記錄：`CHANGELOG.md`（根目錄，以里程碑為單位分組已歸檔的 changes）
- 架構實驗記錄索引：`openspec/experiments/INDEX.md`（每次 `ctx:experiment start/promote/discard` 自動更新）
- **架構發布到 public template**（fork 用）：`ctx:publish` — 若你 fork 此 template 又另開 private 工作 repo，可用此 command 將 archive 過的 changes 發布回你 fork 的 template；發布記錄存於 `openspec/changes/archive/<name>/published.md`

### Claude Commands 位置
- **project-scoped**：`<project-root>/.claude/commands/`（需在該 repo 根目錄）
- **user-scoped**：`~/.claude/commands/`（全局可用，跨所有 repo）
- 兩者不同位置，安裝 OpenSpec 或新增 slash commands 時需確認目標範疇

### Claude Code Hooks 位置
- **Hook scripts**：`.claude/hooks/*.py`（project-scoped、git tracked、跨機透過 git 同步）
- **Hook 註冊**：`.claude/settings.json`（project-scoped）；不要寫 `~/.claude/settings.json`
- **共用 lib**：`.claude/hooks/lib/event_writer.py`——所有 hook 透過這個 lib 寫事件到 `inbox/captured/cc_events/<session_id>/`
- **完整 spec**：`openspec/specs/cc-hooks-capture/spec.md`

### 參考素材（隔離區）
- `_reference/`：非架構、待消化的參考素材，AI 不主動載入。

## Slash Commands 速查表

日常 session 最常用到的 commands，依「工作流意圖」分組。完整定義見 `.claude/commands/ctx|opsx|think/`。

### 工作流：專案 `ctx:project`
| Command | 作用 |
|---|---|
| `/ctx:project new <name>` | 建專案 + `git checkout -b project/<name>` + INDEX.md 登記 |
| `/ctx:project load <name>` | 載入目標/現況/下一步/材料地圖（提到專案名會隱式 load） |
| `/ctx:project update <name>` | Smart-Gather 聚合進度 → 產 work_log |
| `/ctx:project pause <name>` | 狀態改 paused（**分支保留**） |
| `/ctx:project resume <name>` | `git checkout project/<name>` + 狀態改 active |
| `/ctx:project complete <name>` | Retrospective + 最終 `--no-ff` milestone merge + 刪分支 |
| `/ctx:project rename <old> <new>` | 確定性重命名（目錄 + INDEX + frontmatter） |

### 工作流：內容提交 `ctx:content`
| Command | 作用 |
|---|---|
| `/ctx:content` | 偵測變更 → 依「分支類型 × 變更組合」路由矩陣決策 → 混合變更自動拆兩個 commit |
| `/ctx:content merge` | 依當前分支分歧策略：content `--squash`、project 詢問 milestone → `--no-ff` |
| `/ctx:content merge project <X> "<msg>"` | 一行語法 milestone merge（跳過詢問，從任意分支觸發） |

### 工作流：下班總整理 `ctx:eod`
| Command | 作用 |
|---|---|
| `/ctx:eod` | 下班總整理。fetch → 跑 state_audit → 自動處理 bridge-stale / push、詢問 dirty / 舊 content/* / diverged，確保 remote 維持最新、observer 20:00 看得到今日工作。與 18:30 cron silent backstop 共享 `state_audit/core.audit()`。 |

### 工作流：開機總整理 `ctx:onboard`
| Command | 作用 |
|---|---|
| `/ctx:onboard` | 開機 / 早晨 onboarding。fetch → 跑 state_audit → 詢問 dirty 委派 /ctx:content（feature 分支 abort）→ 讀昨夜 audit findings + observer 條目（🔴 axiom watch / 🟡 skill candidate hints）→ active 專案 snapshot → 一頁式 digest 與路由建議。對稱於 /ctx:eod，共用 `state_audit/core.audit()`。 |

### 工作流：架構變更 `ctx:arch` / `opsx:*` / `ctx:merge`
| Command | 作用 |
|---|---|
| `/ctx:arch` | 架構變更工作流入口（討論 → openspec proposal → 開 feature 分支） |
| `/opsx:explore` | Thinking partner 模式（釐清需求） |
| `/opsx:propose <name>` | 產 proposal + design + specs + tasks 一次齊 |
| `/opsx:apply <name>` | 依 tasks.md 逐項實作到目標檔案 |
| `/opsx:archive <name>` | 歸檔到 `openspec/changes/archive/YYYY-MM-DD-<name>/` |
| `/ctx:merge` | 合 `feature/*` 回 main（**只處理 feature**；content/project 會被擋下導向 `/ctx:content merge`） |
| `/ctx:publish` | 將已 archive 的 change 發布到 public template repo（fork 用） |

### 工作流：實驗 / 評估 / 其他
| Command | 作用 |
|---|---|
| `/ctx:experiment start/diff/promote/discard` | 以 git branch 作隔離容器的架構實驗流程 |
| `/think:eval` | 結構化評估「要不要自動化某操作、要怎麼實作」 |

### 三種 merge 策略嚴格分家

| 分支 | 合併指令 | 策略 |
|---|---|---|
| `content/YYYY-MM-DD` | `/ctx:content merge` | `--squash`，分支刪除 |
| `project/<name>` | `/ctx:content merge project <X> "..."` | `--no-ff` + milestone message，**分支續命** |
| `feature/<change-name>` | `/ctx:merge` | `--no-ff` + 文件審查 + 版號 tag |

誤用會被對應指令的 guard 擋下並導向正確指令。

## 命名規則
- 目錄和檔名：小寫 + 下劃線 (snake_case)
- 臨時一次性專案：`tmp_<name>/`

## Python 環境
- 依賴定義於根目錄 `pyproject.toml`，用 `uv sync --all-groups` 安裝
- 每個 skill 的依賴有獨立 group；新增 skill 依賴時在 `pyproject.toml` 新增 group
- 需要隔離時在 `infra/adhoc_jobs/<project>/.venv/` 建獨立環境

## 快速查詢

<!-- 隨著你的專案增長，在這裡新增活躍專案的快捷路由 -->
<!-- 格式：- `project-name` → `adhoc_jobs/project_name/` (說明) -->
