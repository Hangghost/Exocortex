# Exocortex

**三層式 AI 脈絡基礎設施——真正了解你的 AI 第二大腦。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/Hangghost/Exocortex?style=social)](https://github.com/Hangghost/Exocortex/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Hangghost/Exocortex/pulls)
&nbsp;&nbsp;[🌐 English](README.md)

Exocortex 是一個開源核心模板，用於建構個人化 AI agent 系統。它讓你的 AI（Claude、Cursor 等）擁有持久記憶、結構化上下文，以及一個自我演化的知識系統——不綁定任何特定平台或向量資料庫。

---

## 為什麼需要這個

每次 AI 對話都從零開始。AI 不知道你的專案、你的決策風格、你過去的錯誤，也不知道你正在進行的工作。你不斷重複解釋自己。

Exocortex 透過給 AI 一套**結構化的、基於檔案的記憶系統**來解決這個問題——跨 session 持久存在，隨時間自動演化，完全在你的掌控之下。

---

## 適合誰用

**如果你符合以下條件：**
- 每天大量使用 AI 工具（Claude、Cursor、ChatGPT），卻每次都要重新解釋自己的背景
- 希望 AI 永久記住你的專案、偏好與決策風格
- 在乎**擁有**自己的 AI 記憶，不想把它交給黑盒子
- 熟悉 Markdown 檔案和基本 git 操作

**這不是**即插即用的應用程式。它是一套你建構一次、永久擁有的系統。你放入的脈絡越多，AI 就越了解你。

---

## 你能得到什麼

**一個記住你所有事情的 AI**
你的進行中專案、當前工作、過去決策——不需要每次 session 重新解釋。開啟對話，AI 已經知道你上次停在哪裡。

**一個像你一樣思考的 AI**
儲存你的個人決策原則、溝通風格與工作哲學。AI 自動套用它們——給出符合你思維模型的建議，而不是通用的最佳實踐。

**隨時間自動變聰明的記憶**
Observer-Reflector pipeline 自動運行：每日掃描工作日誌提取模式，每週反思將其提煉為持久洞察。使用這套系統越久，你的 AI 就越了解你。

**對 AI 知識的完全所有權**
AI 知道的每一個事實都存在於你掌控的純 Markdown 檔案中。可稽核、可修正、可刪除。沒有黑盒子，沒有平台綁定。

**一份記憶，任何 AI 工具**
同一套脈絡層適用於 Claude Code、Cursor，或任何能讀取檔案的 LLM。切換工具，不會失去 AI 對你的累積認知。

---

## 三層記憶架構

```
┌─────────────────────────────────────────────────────────────────┐
│  L3 — 規則層 (rules/)                                            │
│  永久事實。每次 session 必讀。緩慢演化。                           │
│  → SOUL.md, USER.md, WORKSPACE.md, ARCHITECTURE.md, axioms/     │
├─────────────────────────────────────────────────────────────────┤
│  L1/L2 — 觀測層 (memory/OBSERVATIONS.md)                        │
│  中期訊號。由 Reflector 每週提煉。                                 │
│  → 經過一週考驗後留下的洞察                                        │
├─────────────────────────────────────────────────────────────────┤
│  L0 — 原始訊號層 (contexts/)                                     │
│  短期記錄。由 Observer 每日掃描。                                  │
│  → 工作日誌、研究紀錄、反思、部落格草稿                             │
└─────────────────────────────────────────────────────────────────┘
```

**資料流：** 原始訊號（L0）→ Observer 提取觀測（L1/L2）→ Reflector 將持久洞察晉升至規則層（L3）。

---

## 系統工作流

```
每日 18:30   → State Audit：純規則性狀態檢查（無 LLM）
                → 寫 findings 到 inbox/captured/ + raw_signals/
                → observer 20:00 跑前的最後把關
每日 19:00   → Capture：將 Claude Code hook 事件 bridge 進 raw_signals/
每日 20:00   → Observer：掃描 contexts/ + high-signal raw_signals/，
                寫入 memory/OBSERVATIONS.md
每週 (週日)  → Reflector：提煉觀測，將持久洞察晉升至 rules/
```

兩個 **hero commands** 框住每天的工作節奏——它們是讓「harness」具體可感的東西
（AI 看到的是你整套系統的策展橫切面，不是記憶庫模糊的召回片段）：

| 指令 | 做什麼 |
|---|---|
| `/ctx:onboard` | 早晨一頁式 digest：把昨晚的觀察、早上 inbox 訊號、所有 active 專案的最新進度，整合成「今天該動什麼」。只有 harness 跨整個知識圖譜讀的能力做得到。 |
| `/ctx:eod` | 下班總整理：處理 dirty trees、push、audit findings——確保 20:00 observer 看得到今日工作。 |

兩個指令共享 `state_audit/core.audit()`，看的是同一份事實基底。

**完整指令速查**（依工作流意圖分組）：

| 工作流 | 指令 |
|---|---|
| **專案脈絡** | `/ctx:project new|load|update|pause|resume|complete|rename` |
| **內容提交** | `/ctx:content`（依分支類型 × 變更組合自動路由；混合變更自動拆 commit） |
| **架構變更** | `/ctx:arch` → `/opsx:explore|propose|apply|archive` → `/ctx:merge` |
| **系統健康** | `/ctx:onboard`（早晨）、`/ctx:eod`（傍晚） |
| **架構實驗** | `/ctx:experiment start|diff|promote|discard` |
| **發布到 fork 的 template** | `/ctx:publish`（若你有維護自己 fork 的 template upstream） |
| **決策輔助** | `/think:eval` |

---

## 快速開始

### 1. Fork 此 repo 作為你的個人實例

```bash
# 在 GitHub 建立個人 fork 後：
git clone git@github.com:<your-username>/Exocortex.git exocortex-personal
cd exocortex-personal

# 將此公開 repo 設為 upstream，以便未來同步架構更新
git remote add template git@github.com:Hangghost/Exocortex.git
```

### 2. 個人化核心檔案

填寫以下檔案中的 TODO 欄位：

```
rules/USER.md         ← 你的名字、背景、興趣、溝通風格
rules/ENVIRONMENT.md  ← 你的設備、帳號、工具
rules/SOUL.md         ← 你的 AI 個性與原則（可選）
rules/axioms/INDEX.md ← 你的個人決策原則
```

### 3. 設定定時任務

```bash
# 複製環境範本
cp .env.example .env
# 填入選用的 API keys：
#   ANTHROPIC_API_KEY — 只有跑 Observer/Reflector 才需要
#                        （系統其他部分不依賴 LLM）

# 安裝依賴
uv sync --all-groups

# 測試 state audit（不需要 API key）
python -m infra.periodic_jobs.state_audit.cron

# 測試 capture pipeline（不需要 API key；
# 將 CC hook 事件 bridge 進 raw_signals/）
python -m infra.periodic_jobs.ai_heartbeat.src.v1.capture
```

按照 `infra/periodic_jobs/CRONTAB.md` 設定 cron jobs。最小可用排程
其實只有 **state_audit 18:30**——Observer/Reflector 是需要 Anthropic API
的選用加值。

### 4. 安裝 Claude Code 指令

如果你使用 Claude Code，`.claude/commands/` 中的 slash commands 在你開啟此 repo 時會自動生效。

---

## 目錄結構

```
Exocortex/
├── rules/                    # L3：永久規則層
│   ├── SOUL.md               # AI 身份與原則
│   ├── USER.md               # 你的個人資料（請個人化）
│   ├── ENVIRONMENT.md        # 你的設備與工具
│   ├── WORKSPACE.md          # 目錄路由指南
│   ├── ARCHITECTURE.md       # 系統架構參考
│   ├── CORE.md               # 跨 agent 共享協定
│   ├── COMMUNICATION.md      # 互動風格指南
│   ├── axioms/               # 個人決策原則
│   └── skills/               # 可複用的 AI agent 能力
├── contexts/                 # L0：原始訊號（你的日常記錄）
│   ├── work_logs/            # 任務執行與進度
│   ├── survey_sessions/      # 研究與調查
│   ├── thought_review/       # 反思與覆盤
│   └── blog/                 # 寫作草稿
├── memory/
│   └── OBSERVATIONS.md       # L1/L2：Observer 輸出（自動寫入）
├── inbox/                    # 快速捕獲
│   ├── todos.md
│   ├── ideas.md
│   └── reading_list.md
├── registry/                 # 跨系統路由索引
│   ├── dev.md                # 活躍 repo 與開發脈絡
│   ├── career.md             # 職涯與技能
│   ├── life.md               # 目標與學習
│   └── library.md            # 個人圖書館指標（選用）
├── projects/                 # 活躍專案脈絡
│   └── INDEX.md              # 專案登錄表
├── library/                  # 個人文件索引卡（選用）
├── openspec/                 # 架構變更工作流
│   ├── specs/                # 已提交的能力規格
│   └── changes/              # 進行中與已歸檔的變更
├── infra/
│   ├── state/                # Periodic role 協調（system_state.json + helpers）
│   ├── periodic_jobs/
│   │   ├── state_audit/      # 純規則性健康檢查（無 LLM）
│   │   └── ai_heartbeat/     # Observer/Reflector/Capture pipeline（依賴 LLM）
│   └── tools/                # 工具腳本
└── .claude/
    ├── commands/             # Claude Code slash commands
    ├── hooks/                # CC hooks（at-source capture，寫進 inbox/captured/cc_events/）
    └── settings.json         # Hook 註冊
```

---

## 設計哲學

### 為什麼用檔案，不用資料庫？

Git 上的 Markdown 檔案：
- **透明** — 你可以讀取、編輯、稽核所有內容
- **可移植** — 適用於任何 AI 工具、任何編輯器、任何平台
- **版本控制** — 完整記錄你的第二大腦如何演化
- **AI 友善** — LLM 大量訓練於 Markdown；結構化標題 = 結構化思維

### 為什麼採用三層設計？

這三層對應認知科學原則：
- **L3（規則）** → 長期記憶：關於你是誰的穩定事實
- **L1/L2（觀測）** → 語義記憶：從經驗中提取的模式
- **L0（脈絡）** → 情節記憶：具體的事件與記錄

Observer-Reflector pipeline 是記憶鞏固機制——就像睡眠對人類記憶的作用。

### 為什麼不直接用 ChatGPT 記憶 / 內建 AI 記憶？

內建記憶是黑盒子。你無法稽核儲存的內容，無法修正錯誤的記憶，無法控制什麼被晉升。Exocortex 讓你對 AI 記憶擁有**完全的所有權**。

---

## 致謝

深受 [grapeot/context-infrastructure](https://github.com/grapeot/context-infrastructure) 啟發——最早將結構化 AI 脈絡作為個人記憶系統來探索的先驅作品。

---

## 貢獻

歡迎架構改進、新 skills 和 pipeline 增強。個人資料、私有整合和特定領域內容屬於你的個人 fork。

貢獻前，請先閱讀 `rules/ARCHITECTURE.md` 了解系統設計原則。

---

## 授權

MIT
