# ARCHITECTURE.md - 系統架構地圖

記錄各區塊的設計意圖、邊界、關係與資料流。**查閱時機**：設計新功能、架構變更前，或需要了解「為什麼這樣設計」時。

---

## 頂層架構圖

```
Exocortex/
├── rules/          ← L3 全局約束層（靜態，每 session 被動載入）
│   ├── CORE.md         session 協定 SSOT
│   ├── WORKSPACE.md    路由速查
│   ├── ARCHITECTURE.md 架構地圖（本檔）
│   ├── SOUL.md         agent 人格
│   ├── USER.md         使用者檔案
│   ├── ENVIRONMENT.md  環境事實
│   ├── COMMUNICATION.md 溝通規範
│   ├── axioms/         核心公理
│   └── skills/         可複用技術方案（AgentSkills 標準格式）
│
├── memory/         ← 系統記憶（observer/reflector 產出）
│   └── OBSERVATIONS.md append-only 歷史事件流
│
├── contexts/       ← 使用者產出的上下文（L1/L2，主動拉取）
│   ├── blog/           部落格文章草稿與主動思考產物
│   ├── work_logs/      任務執行紀錄
│   ├── survey_sessions/ 研究報告
│   └── thought_review/ 思考覆盤
│
├── library/        ← 個人 library（index cards，AI-agent native；選用）
│   ├── INDEX.md        所有珍藏文件一覽表
│   ├── README.md       card 格式規範與新增流程
│   └── <cards>/        個別 index card（摘要、標籤、file_path）
│                       binary 本體放在使用者自選的 local 文件目錄（不入 git）
│
├── registry/       ← 跨系統路由索引
│   ├── career.md       履歷、工作、技術能力
│   ├── dev.md          活躍 repo、開發筆記
│   ├── life.md         目標、學習、待辦
│   └── library.md      個人 library 路由入口
│
├── projects/       ← 專案脈絡層（progressive disclosure）
│   ├── INDEX.md        所有專案一覽索引（被動載入）
│   └── <name>/
│       ├── PROJECT.md  核心脈絡（目標、現況、下一步、決策、材料地圖）
│       └── context/    按需載入的深度技術文件（technical.md、environment.md 等）
│
├── inbox/          ← 快速捕獲區
│   ├── todos.md        待辦事項
│   ├── reading_list.md 閱讀清單
│   ├── ideas.md        靈感捕獲
│   └── captured/       外部匯入的 raw notes
│
├── openspec/       ← 架構變更設計文件（提案、設計、任務）
│   ├── changes/        進行中的變更
│   ├── specs/          已同步的能力 spec
│   └── experiments/    架構實驗索引
│
├── infra/          ← 基礎設施層
│   ├── tools/          可複用工具指令碼
│   ├── state/          系統執行狀態紀錄（system_state.json + helper）
│   ├── periodic_jobs/  自動化定時任務
│   │   ├── CRONTAB.md   排程設定參考
│   │   ├── state_audit/ 規則性狀態審計（無 LLM）
│   │   └── ai_heartbeat/  observer.py（日）、reflector.py（週）
│   └── adhoc_jobs/     一次性專案與指令碼
│
└── _reference/     ← 隔離區（非架構，AI 不主動載入）
```

---

## 各區塊設計意圖與邊界

### `rules/` — L3 全局約束層

**意圖**：儲存在每個 session 開始時被動載入的固定知識——agent 人格、環境事實、行為協定、路由規則。這層的內容是系統的「靜態配置」，不隨工作進展改變。

**邊界**：只放「跨 session 永遠成立的事實與規則」。不放進行中任務的狀態、一次性記錄、或程式碼。

**CORE.md 的特殊地位**：所有 agent 的 SSOT，定義 session 閱讀順序與跨 agent 共享行為。所有 agent（Claude Code、Cursor 等）應都參照此檔案，不各自維護 session 協定。

### `memory/` — 系統記憶層

**意圖**：儲存 observer/reflector 的產出——append-only 的歷史事件流。`OBSERVATIONS.md` 是事件、觀察、學習的唯一存儲，只增不改。與 `contexts/`（使用者產出）語意清晰分離：`memory/` = 系統產出，`contexts/` = 使用者記錄。

**邊界**：只放 observer/reflector 的輸出。不放使用者產生的記錄，不放規則或配置。

### `contexts/` — 使用者上下文層

**意圖**：儲存使用者產出的可更新紀錄——部落格文章草稿、工作記錄、研究報告、思考覆盤。需要主動查詢時拉取。

**觀察設定 SSOT**：`contexts/MANIFEST.md` 定義各子資料夾的觀察 schema（`observation_mode`、`extraction_focus`），是 observer 掃描設定與新增資料夾設計準則的單一真實來源。

**邊界**：不放規則或全局配置。不放 observer 產出（那是 `memory/`）。不主動載入——需要歷史脈絡時才讀。

### `inbox/` — 快速捕獲區

**意圖**：低門檻的碎片捕獲，先記後整理。`todos.md`（待辦）、`reading_list.md`（閱讀清單）、`ideas.md`（靈感）各有獨立格式與生命週期；`captured/` 暫存外部匯入的 raw notes。

**邊界**：暫存區，不是最終存儲。消化後分流至 `contexts/`、`projects/`、`openspec/` 等。

### `projects/` — 專案脈絡層

**意圖**：以 progressive disclosure 組織各個進行中專案的知識，讓 AI 在任意 session 中能快速回到工作狀態。採用三層結構：
- `INDEX.md`（被動載入）：所有專案的一行摘要
- `PROJECT.md`（`/ctx:project load` 時載入）：目標、現況、下一步、關鍵決策、材料地圖
- `context/`（AI 按需自行拉取）：技術細節、環境設定等深度文件

**生命週期狀態**：專案 status 有四個合法值，形成單向狀態機：
```
active ──→ paused ──→ active (resume)
  │
  └──→ completed ──→ archived
```
- `active`：進行中，observer staleness check 生效（超過 14 天未更新觸發 🟡 提醒）
- `paused`：暫停中，不觸發 staleness check；load/update 時提醒重新啟動
- `completed`：已完成，frontmatter 含 `completed_date`，不觸發 staleness check
- `archived`：歸檔，不出現在日常操作建議中

**work_log 橋樑設計**：`/ctx:project update` 和 `/ctx:project complete` 產出 work_log 到 `contexts/work_logs/`（分別命名為 `_update.md` 和 `_retrospective.md`），讓 observer 透過既有 work_logs 通道觀察到專案更新中的經驗，而不需要 observer 直接掃描 `projects/` 目錄。

**邊界**：PROJECT.md 是「地圖」，不是「搬家」——材料（work_logs、surveys、code）留在原位，PROJECT.md 只放路徑指針。`context/` 下可能含敏感資訊（帳號、endpoints），設計上不自動載入。

### `library/` — 個人 Library 層（選用）

**意圖**：AI-agent native 的個人文件索引。只在 repo 中存放 markdown index cards（摘要、標籤、原始路徑），binary 本體（PDF、影片等）由使用者放在自選的 local 文件目錄，不進入 git。AI 透過 card 的 `file_path` 欄位定位到本地檔案，查找成本只多一步（讀 card → 得到路徑）。路由入口：`registry/library.md`。

**邊界**：只放 index cards（純文字 markdown）。binary 不進 git，由使用者自行管理備份。observer 暫不掃描 library/（不在 contexts/ 下，不受 MANIFEST.md 管轄）。

### `registry/` — 跨系統路由索引

**意圖**：跨系統任務（履歷更新、開發、生活規劃）的資訊入口，指向各外部系統中的 SSOT。Agent 在執行跨系統任務前先查 registry，找到正確的資訊來源。

**邊界**：只放「去哪裡找什麼」的指針，不放內容本身。

### `infra/` — 基礎設施層

**意圖**：將「讓系統運作的程式碼」收納在一個命名空間下，不搶認知層注意力。四個子目錄各有職責：
- `state/`：系統執行狀態紀錄。`system_state.json`（git-tracked）為各 periodic role（observer / reflector / state_audit / capture / triage_*）的全域 high-water mark cache，consumer（如 opsx:archive）讀取「上次成功跑到哪」做協調決策。`lib.py` 提供 `read_system_state()` / `update_role_state()` / `write_run_log()` 三個共用 helper，皆採用 atomic write。互補的 audit log 落在 `raw_signals/<date>/<role>_run.json`（不進 git）。
- `periodic_jobs/`：自動化定時任務，依職責拆成平行子角色。排程設定參考見 `infra/periodic_jobs/CRONTAB.md`。
  - `ai_heartbeat/`：observer.py 每日執行產生觀察，reflector.py 每週合成反思。輸出流向 `memory/`。**依賴 LLM API**（如 Anthropic API）。屬 **Behavior Pipeline**（觀察使用者做了什麼）。
  - `state_audit/`：純規則性的儲存庫狀態審計角色。`core.audit()` 跑八項檢查（dirty / unmerged content/* / bridge-stale / unpushed-or-untracked-remote / branch-behind-origin / missed-observer-or-reflector-run / role-failed-run / stale-running-role），cron.py 每日 18:30 silent backstop 寫 `inbox/captured/<date>_state_audit.md` + `raw_signals/<date>/state_audit.json`。**無 LLM、無 API 依賴**——只用 Python 標準庫 + git CLI。與 `/ctx:eod`、`/ctx:onboard` 命令共享 `core.audit()`。`role-failed-run` 為通用檢查：scan `system_state.json` 中所有 `roles.*.last_status == "failed"`，已知角色走 `ROLE_RECOVERY_HINTS` 給 bespoke 修法、未知角色 fallback 到 generic hint，新增 periodic role 自動納入監控。
- `tools/`：可複用工具指令碼
- `adhoc_jobs/`：一次性專案與指令碼

**邊界**：只放「讓系統運作的程式碼」。手動研究或任務紀錄放 `contexts/`。認知產物（規則、記憶、脈絡）不放此處。`infra/state/` 是元件協調用的 metadata，不是 observation 或記憶（因此不放 `memory/`）。

### Hooks 設計原則 — Cross-worktree 可用性

`.claude/hooks/` 與 `.claude/settings.json` 屬 **infra-shaped** 元件：必須在主 worktree 與任何 `.claude/worktrees/<name>/` 下開的 session 都正確執行，不論該 worktree 的 branch 是否 check in 這些檔案。

**核心規則**：`.claude/settings.json` 內所有 `hooks.<event>[].hooks[].command` 字串 **必須使用 `$CLAUDE_PROJECT_DIR/.claude/hooks/<script>` 絕對路徑前綴**。禁止相對路徑（如 `.claude/hooks/<script>`）或硬編碼絕對路徑。

**為什麼**：Claude Code 解析 hook command 的相對路徑時以 session cwd 為基準。當 session 跑在 `.claude/worktrees/<name>/` 且該 worktree 的 branch 未 check in `.claude/hooks/`（典型情境：long-lived `project/*` branch，依設計不自動同步 main），相對路徑會失敗，capture hook 全部 missing，capture pipeline 對該 worktree 完全失能。`$CLAUDE_PROJECT_DIR` 是 Claude Code 注入到 hook context 的 env var，永遠指向主 repo root。

**內外對稱**：本原則與 `event_writer` 從 cwd 解析回主 repo root 的內部邏輯互為對稱——shell 層由 `$CLAUDE_PROJECT_DIR` 進到主 repo 的 hook 腳本，Python 層由 `event_writer` 從當前 cwd 解析回主 repo root。任何只改一邊的「修法」都會留下隱性 bug。

**Review 機械檢查**：`grep -E '"command"\s*:\s*"\.claude/' .claude/settings.json` 應為空輸出。

### `rules/skills/` — 系統 Skills

**意圖**：儲存跨 agent 可攜的可複用能力知識——工作流、最佳實踐、API 指南。採用 [AgentSkills 開放標準](https://agentskills.dev) 格式，使任何支援標準的 agent（Claude Code、Cursor、Gemini CLI、OpenCode 等）都能直接發現與載入，無需額外轉換。

**結構**：每個 skill 以子目錄形式存在，目錄名為 kebab-case，目錄內必須包含 `SKILL.md`：

```
rules/skills/
├── INDEX.md              ← 能力速查 manifest（session 啟動時被動載入）
└── <skill-name>/
    ├── SKILL.md          ← 主體（AgentSkills frontmatter + 完整指令）
    ├── references/       ← 延伸資源（按需載入）
    └── scripts/          ← 輔助腳本（按需載入）
```

**`SKILL.md` frontmatter 必填欄位**：`name`、`description`。這兩個欄位也會反映在 `INDEX.md` 表格中。

**邊界**：只放「可複用、跨任務、跨 agent 均有效」的能力。一次性工作流或 agent-specific 指令放 `.claude/skills/`（或對應 agent 的 skills 目錄），不放此處。Axioms（決策原則）維持在 `rules/axioms/`，不混入。

### `openspec/` — 架構變更工作流

**意圖**：記錄架構變更的設計過程（提案、設計決策、任務清單）。`changes/` 是進行中的變更，`specs/` 是已同步到系統的能力規格，`experiments/` 是架構探索性實驗記錄（`ctx:experiment` 工作流產出）。

**邊界**：只在 ctx:arch 工作流中產生和修改。不直接在此執行實作——實作在對應的目標檔案（`rules/`、`.claude/` 等）中進行。

### `_reference/` — 隔離區

**意圖**：存放非架構性的參考素材，AI 不主動載入。包含待消化的工具腳本與外部文件，僅供人工查閱或手動遷移。

---

## 區塊間關係

```
CORE.md (rules/)
  └─ 定義 session 閱讀順序 ──→ SOUL, USER, ENVIRONMENT, WORKSPACE, COMMUNICATION

WORKSPACE.md (rules/)
  └─ 路由速查 ──→ memory/, contexts/, registry/, projects/, inbox/, openspec/, infra/

registry/ ──→ 外部系統（issue trackers、文件平台等）

infra/periodic_jobs/ai_heartbeat/
  ├─ observer.py ──→ memory/OBSERVATIONS.md
  └─ reflector.py ──→ memory/OBSERVATIONS.md

openspec/changes/<name>/
  └─ opsx:apply 實作後 ──→ rules/, .claude/commands/, 其他目標檔案

infra/adhoc_jobs/<project>/
  └─ 產出物 ──→ contexts/work_logs/ 或 contexts/survey_sessions/

inbox/
  └─ 消化後分流 ──→ contexts/, projects/, openspec/changes/
```

---

## Skills 系統設計

### 三層架構

Skills 分三層，由外到內依序疊加：

| 層級 | 位置 | 作用域 | 維護者 |
|------|------|--------|--------|
| **系統 skills** | `rules/skills/` | 此 repo，跨 agent | Repo（人工 + Reflector 晉升） |
| **Agent 專案 skills** | `.claude/skills/`（repo 根目錄） | 此 repo，此 agent | 專案層設定 |
| **Agent 全域 skills** | `~/.claude/skills/` | 所有 repo，此 agent | 使用者全域設定 |

Agent 在 session 中應將三層合併視為完整能力圖：**系統 skills + agent 專案 skills + agent 全域 skills = 本次 session 可用能力全集**。

三層各有職責：系統 skills 追求跨 agent 可攜性；agent 專案 skills 承載此 repo 的特定工作流（如 opsx:*、ctx:*、think:*）；agent 全域 skills 承載跨 repo 通用的 agent 能力。

### 命名空間語意

`.claude/commands/` 下的 agent 專案 commands 以命名空間組織，各有清楚的語意邊界：

| 命名空間 | 定位 | 典型工具 |
|---------|------|---------|
| `ctx:` | 架構開發工具：專案脈絡、內容提交、git 工作流、架構實驗、發布 | `ctx:project`、`ctx:content`、`ctx:arch`、`ctx:merge`、`ctx:experiment`、`ctx:publish` |
| `opsx:` | OpenSpec 設計流程工具：探索、提案、實作、歸檔 | `opsx:explore`、`opsx:propose`、`opsx:apply`、`opsx:archive` |
| `think:` | 日常使用框架時的思考輔助工具：評估、判斷、覆盤 | `think:eval` |
| （無命名空間） | 跨 repo 通用工具，適合放 `~/.claude/commands/` | — |

**歸屬判斷**：新增 command 時，依據「這個工具在什麼情境下使用？」判斷命名空間。若不確定，可用 `/think:eval` 評估。

**完整日常操作速查表**：見 `rules/WORKSPACE.md` 的「Slash Commands 速查表」一節，依工作流意圖分組列出所有 commands、三種 merge 策略的分家規則。

### AgentSkills 標準格式

`SKILL.md` 使用 YAML frontmatter 宣告 metadata：

```markdown
---
name: skill-name
description: 一行描述，說明此 skill 解決什麼問題
# 可選欄位：version, author, tags, trigger_patterns 等
---

# Skill 主體內容
...
```

此格式為開放標準，主流 agent 均原生支援。對不支援的 agent，SKILL.md 仍是可讀的 markdown，降級優雅。

### Progressive Disclosure 載入機制

Agent 讀取 skills 時遵循三層按需展開，避免 context 膨脹：

```
Session 啟動
  → 讀 rules/skills/INDEX.md（metadata only，~100 tokens/skill）
      ↓ 判斷任務需要某個 skill
  → 讀 rules/skills/<name>/SKILL.md（完整指令）
      ↓ 執行時需要延伸資源
  → 讀 references/ 或 scripts/（最按需）
```

**INDEX.md 設計原則**：只列 `name` + `description`，不嵌入完整 SKILL.md 內容。每新增或刪除 skill 必須同步更新 INDEX.md。

### Reflector 晉升流

L2 Reflector 識別出 `memory/OBSERVATIONS.md` 中的高優工作流觀察時，晉升流程：

```
reflector.py 識別高優觀察
  → 在 rules/skills/<name>/ 建立子目錄
  → 寫入符合 AgentSkills 格式的 SKILL.md
  → 更新 rules/skills/INDEX.md 新增條目
  → append 晉升事件到 memory/OBSERVATIONS.md
```

晉升後的 skill 在下一個 session 即可被任何 agent 發現。

---

## 資料流圖

### Session 初始化流

```
Agent 啟動
  → 讀 CORE.md（session 協定）
  → 讀 SOUL.md, USER.md, ENVIRONMENT.md, WORKSPACE.md, COMMUNICATION.md
  → 讀 rules/skills/INDEX.md（系統 skills metadata）
  → 合併 agent 全域 skills（~/.claude/skills/）
  → 合併 agent 專案 skills（.claude/skills/）→ 完整能力圖
  → 依任務類型：讀 registry/<domain>.md
  → 依需求：拉取 memory/OBSERVATIONS.md 或 projects/INDEX.md
```

### 記憶累積流

```
每日 18:30：state_audit/cron.py（純規則，無 LLM）
  → git fetch --all
  → 八項檢查（dirty / unmerged content/today / bridge-stale / unpushed / branch-behind-origin
              / missed-observer-or-reflector / role-failed-run / stale-running-role）
  → 寫 raw_signals/<date>/state_audit.json（永遠寫，給 observer 讀）
  → 寫 inbox/captured/<date>_state_audit.md（findings 非空時）
  → 寫 raw_signals/<date>/state_audit_run.json + 更新 infra/state/system_state.json

即時：CC hooks（SessionStart / UserPromptSubmit / SessionEnd / PostToolUseFailure(Bash) / SubagentStart / SubagentStop）
  → .claude/hooks/*.py 寫 inbox/captured/cc_events/<session_id>/{session.json | <event_type>_<ts>_<uuid>.json}
  → SessionStart 寫單檔 session.json header（cwd / transcript_path / source / model 等 session 級欄位），覆寫式
  → 其餘 event hook 寫 event delta（不重抄 session 級欄位，由 bridge 從 session.json join）
  → Hook 層 stateless write-only，無網路 / 無 LLM；失敗 fallback 到 ~/.claude/logs/hooks_failed/

每日 19:00：ai_heartbeat/v1/capture.py
  → L0 triage source（單一）：cc_events_bridge（讀 inbox/captured/cc_events/ → raw_signals）
     bridge 過濾 metadata-only event_type（session_done / subagent_start），inbox 留檔等 30 天 GC
  → 三級分流 → 寫 raw_signals/<date>/cc_event_<event_type>_<id>.json
  → 各 phase 寫 raw_signals/<date>/<role>_run.json（capture / triage_stage1 / triage_stage2）+ 更新 infra/state/system_state.json

每日 20:00：ai_heartbeat/v1/observe.py
  → 讀 infra/state/system_state.json 做冪等性檢查（fallback 至 grep OBSERVATIONS.md）
  → 讀 raw_signals/<date>/state_audit.json（meta block）
  → 讀 raw_signals/<date>/*.json 中 triage="high" 的 capture signals
  → 讀取 contexts/MANIFEST.md（各子資料夾觀察設定）
  → 分析 contexts/ 近期變更（依 MANIFEST.md 的 observation_mode）
  → 用 system_state.observer.last_finished_at 當 high-water mark 掃 openspec/changes/archive/（fallback 至 -mtime -1）
  → 產生觀察條目（開頭含 [meta] 區塊）
  → append → memory/OBSERVATIONS.md
  → 寫 raw_signals/<date>/observer_run.json + 更新 infra/state/system_state.json

每週：reflector.py
  → 合成近期觀察
  → 產生反思條目
  → append → memory/OBSERVATIONS.md
  → 寫 raw_signals/<date>/reflector_run.json + 更新 infra/state/system_state.json

opsx:archive（producer-aware）
  → 讀 infra/state/system_state.json
  → 若 observer 已跑當天 → 詢問 roll(tomorrow) / stay(today + _late.json)
  → 否則 → today 命名（既有行為）

使用者主動：/ctx:eod
  → git fetch + state_audit.core.audit()（與 cron 共享）
  → 自動處理 bridge-stale + push；詢問 dirty / 舊 content/* / diverged
  → 輸出結尾報告（✅ remote 全部最新 / ⚠️ N 項待處理）

使用者主動：/ctx:onboard
  → git fetch + state_audit.core.audit()（與 /ctx:eod 對稱共享）
  → 詢問 dirty 委派 /ctx:content（feature 分支 abort）
  → 讀 inbox/captured/<yesterday>_state_audit.md
  → 讀 memory/OBSERVATIONS.md 最近條目，分流呈現
      ├─ 🔴 Axiom watch（被動高亮，reflector weekly 蒸餾）
      └─ 🟡 Skill candidate hints（[工作流/*][流程/*][方法論/*] tag 過濾）
  → 讀 projects/INDEX.md + 各 PROJECT.md「下一步」段落
  → 輸出一頁式 digest + 路由建議（不自動 commit / push / 切分支 / 呼叫 LLM）
```

### 架構變更流

```
/ctx:arch
  → /opsx:explore（釐清意圖）
  → /opsx:propose（產出 openspec/changes/<name>/）
  → git checkout -b feature/<name>
  → /opsx:apply（實作到目標檔案）
  → /ctx:merge（合併回 main，確認 ARCHITECTURE.md 是否需更新）
```

### 分支拓樸與內容流

```
content/YYYY-MM-DD ──[--squash]──→ main      (daily snapshot, 分支刪除)
                                      ↑
project/<name> ──[--no-ff milestone]──┘      (分支續命到 complete)
                                      ↑
feature/<change-name> ──[--no-ff]─────┘      (架構變更，分支刪除)
```

- `content/*` 涵蓋 `contexts/`、`memory/`、`inbox/` 等 event-shaped 變更
- `project/*` 涵蓋 `projects/<name>/` state-shaped 變更，long-lived 不自動同步 main
- `feature/*` 涵蓋 `rules/`、`.claude/`、`openspec/` 架構層變更
- 混合變更由 `/ctx:content` 自動拆分；`/ctx:content merge` 處理 content/project，`/ctx:merge` 處理 feature
- **observer 邊界保留**：observer 不掃 `projects/`；專案事件流透過 `/ctx:project update` 產出 `contexts/work_logs/` 條目，隨 `content/*` 進 main 後才被 observer 觀察到（`projects/` 區段詳述）
- 完整 spec：`openspec/specs/project-branch-flow/spec.md`

---

## 擴展點

| 擴展類型 | 放置位置 | 需要更新的文件 |
|---|---|---|
| 新增頂層目錄 | 頂層 | `rules/WORKSPACE.md`（路由）、`rules/ARCHITECTURE.md`（本檔）、`registry/<domain>.md`（若需路由入口） |
| 新增 rules/ 規則文件 | `rules/` | `rules/CORE.md`（若需加入 session 閱讀清單） |
| 新增 registry 域 | `registry/` | `rules/WORKSPACE.md`、`rules/CORE.md` |
| 新增 agent-specific skill/command | `.claude/commands/` 或 `.claude/skills/` | 對應 agent 的 skills 目錄（不需更新系統 skills INDEX） |
| 新增 `think:` 命名空間工具 | `.claude/commands/think/` | `rules/ARCHITECTURE.md`（本檔，說明用途與邊界） |
| 新增自動化腳本 | `infra/periodic_jobs/<role>/` | `infra/periodic_jobs/CRONTAB.md`（時間線總覽 + 核心任務說明 + 示例 crontab）；若新增獨立角色（非掛在既有 ai_heartbeat / state_audit 之下），同步更新 `rules/ARCHITECTURE.md` 的 infra/ 段落與資料流圖。**新角色 SHALL 接入 `infra/state/lib.py`**：執行流程包入三段論（running → ok / failed），每個階段呼叫 `update_role_state()`；完成時呼叫 `write_run_log()`。讓未來的 missed-run 偵測與 cross-role 協調可以直接適用。 |
| 新增 CC hook | `.claude/hooks/<event>.py` + `.claude/settings.json` | Hook script 用 Python stdlib（依賴 `.claude/hooks/lib/event_writer.py`），失敗不阻塞 user input；若事件需被 capture 消化則更新 `cc_events_bridge.py` 的 `_build_content()` 與 spec 的 event_type 列表。Hook 寫入 `inbox/captured/cc_events/<session_id>/`（gitignored），bridge 為 batch consumer。**兩層分離**：Hook 即時 stateless write-only，bridge cron 批次轉 raw_signals。**Schema 兩層**：session 級欄位（cwd / transcript_path / source / model）由 SessionStart hook 寫 `session.json` 單檔，event 檔只記事件特有欄位，bridge 在 join 時 fold 進 raw_signals。**`.claude/settings.json` 引用 hook command 必用 `$CLAUDE_PROJECT_DIR/.claude/hooks/<script>` 絕對路徑前綴，禁止相對路徑**——詳見「Hooks 設計原則 — Cross-worktree 可用性」段落。 |
| 新增系統 skill | `rules/skills/` | `rules/skills/INDEX.md` |
