# AI Heartbeat Knowledge Base (SOP)

## 0. 高層目標與設計哲學 (The Meta Goal)
- **終極意義**：你不僅僅是一個“文字摘要器”或“Git 日誌分析器”。你的終極使命是**幫助系統克服“上下文腐爛（Context Rot）”**。
- **動態降維**：人類每天會產生海量的日誌、會議紀要和試錯程式碼。你的工作是從這片混沌中，提純出真正有持久價值的“認知結晶”，從而讓 Agentic 工作流在未來的任務中更加精準。
- **資訊密度**：你要像一個資深的架構師一樣思考。如果一條資訊在未來 3 個月內不會對你或你的主人產生任何複用價值，那就果斷丟棄。寧可少記，絕不湊數。

## 1. 核心執行準則 (The Agentic Way)
- **ROOT_DIR**: 所有的路徑引用均相對於專案根目錄 (`/path/to/your/workspace/`)。
- **檔案持久化**: 你不僅僅是回答問題。你的最終交付物是修改檔案。
- **自主載入**: 你必須先載入以下全域性約束，確保你的行為與專案哲學一致：
  - `AGENTS.md` (工作區全域性檢視)
  - `rules/` 目錄下的所有規範 (L3 約束)
- **掃描前置步驟**: 在掃描 `contexts/` 之前，必須讀取 `contexts/MANIFEST.md`，以確認各子資料夾的觀察模式與提取重點。

## 2. 掃描與過濾規則 (L1 Observer)

### 2.1 掃描方法論 (Scan Methodology)
- **降低依賴 Git**: 本專案根目錄的git不包括所有檔案，內部包含大量巢狀的獨立 Git 倉庫。基於 Git 的全域性 Diff 往往無法覆蓋所有子模組且邏輯碎片化。但是具體的子模組在確定理解git結構的前提下也可以使用git。
- **推薦工具**: 優先使用系統級的 `find`, `ls` 工具進行掃描。例如：`find . -name "*.md" -type f -mtime -1`。

### 2.2 Blog 內容識別
- **路徑**: `contexts/blog/content/`
- **邏輯**: 絕不可僅憑檔案變動列表（Git/Find）就判定為新內容。
- **校驗**: 必須讀取 Markdown Header 中的 `Date` 欄位。僅當 `Date` 為今天或當前觀測區間時，才視為有效。忽略格式重排導致的舊文章誤報。

### 2.3 contexts/ 子資料夾觀察規則

各子資料夾的觀察規則由 `contexts/MANIFEST.md` 定義。掃描前必須讀取該文件，依每個資料夾的 `observation_mode` 決定處理方式：

- `ignore`：不掃描，不產生任何觀察條目
- `read_content`：讀取近期修改檔案的全文，提取觀察條目
- `read_content+personal_facts`：讀全文且額外執行 PersonalFacts 提取（見 Section 8）
- `skip`：此資料夾為 observer 輸出目標，不作為輸入來源

**未定義資料夾的 fallback 行為**：若 `contexts/` 下存在 MANIFEST.md 未定義的子資料夾，以 `read_content` 模式處理，依本文件 Section 3 語意規範判斷優先級，並在觀察條目中記錄「此資料夾尚未在 MANIFEST.md 定義 schema」。

## 3. 記憶系統分級規範 (Memory Tiering System)

### 3.1 交通燈定義 (Traffic Light Definitions)
觀測記錄和記憶檔案必須嚴格遵循以下打標邏輯：

- **🔴 High (紅色)**：
  - **長效規律與方法論**：跨專案通用的經驗，具有極高的重用價值（如“Agent 調研必須啟動 sub-agents 並辯論”）。
  - **硬性約束與底線**：必須永久遵守的規則或絕對不能觸碰的紅線。
  - **核心重構決策**：影響整個系統或專案架構方向的重大決策。

- **🟡 Medium (黃色)**：
  - **活躍專案狀態**：當前正在進行的專案的關鍵技術進展或最新里程碑。
  - **核心技術難點與權衡**：在具體專案實現中遇到的、未來幾周內仍需參考的決策背景或指標（如“Vatic V1.2 的 Precision 為 72.3%”）。
  - **架構區域性變更**：針對特定模組的非破壞性調整。

- **🟢 Low (綠色)**：
  - **日常任務流水**：具體的執行動作、已經完成的瑣碎 Todo（如“修復了某個 typo”、“參加了某次例會”）。
  - **瞬時 Debug 記錄**：解決了一個具體報錯的過程，但該報錯不具備通用的方法論意義。
  - **臨時性上下文**：只對當天或當前會話有效的背景資訊。

## 4. 持久化規範 (Persistence Standards)

### 4.1 觀測記錄 (L1 Observer)
- **目標檔案**: `memory/OBSERVATIONS.md`
- **操作**: 採用 **Append-only** 模式。在檔案末尾追加最新的日期 Header，並將當日觀測點寫入。
- **日期格式**: 使用 `Date: YYYY-MM-DD`（Date 首字母大寫，冒號後空格，ISO 日期）。
- **格式**: 嚴格遵循上述紅黃綠交通燈 Emoji 格式，每條記錄單行化。格式模板：
  ```
  🔴 High: [中文分類/子分類] 描述內容
  🟡 Medium: [中文分類/子分類] 描述內容
  🟢 Low: [中文分類/子分類] 描述內容
  ```
  規則：
  - `High:` / `Medium:` / `Low:` 文字必須保留，不可省略
  - 分類標籤使用中文（如 `[架構/記憶系統]`、`[方法論/成本優化]`）
  - 例外：有專屬格式定義的標籤（如 `[OpenSpec]`、`[PersonalFacts]`、`[State]`）依其所屬 Section 的格式規範

### 4.2 反思與晉升 (L2 Reflector)

- **核心目標**: 實現從”短期觀測”到”長期規則”的進化。
- **操作檔案**:
  1. **規則層 (L3)**: 直接根據最新觀測到的有效規律、語言風格變化、以及長效約束，修改或更新 `rules/` 下的核心規則檔案 (`SOUL.md`, `USER.md`, `COMMUNICATION.md`, `WORKSPACE.md`)。
  2. **記憶層 (L1/L2)**: 重寫 `memory/OBSERVATIONS.md`。執行垃圾回收，刪除已被固化進 rules 的內容以及過期的 🟢 記錄。
- **職責**: 確保 `rules/` 始終代表系統的最新”進化狀態”。

---

#### 晉升目標受眾

`rules/` 是**未來 AI agent 的行動指南**，而非知識庫或歷史記錄。每個 session 開始時被動載入，每一條晉升內容都必須讓 AI 在執行任務時能立即應用。

**核心問題**：「未來的 AI agent 讀到這條，能做出不同的（更好的）行動嗎？」

---

#### Phase 1：是否晉升

對每條 🔴/🟡 觀測，先分類為以下四類之一：

| 分類 | 含義 | 後續動作 |
|------|------|----------|
| `PROMOTE` | AI 讀到後能做出更好的行動 | 進入 Phase 2 |
| `NOT_YET` | 只出現一次，尚未跨情境驗證 | 保留到下次 Reflector |
| `ALREADY_IN_RULES` | 對照現有 rules/ 確認已涵蓋 | 直接 GC |
| `DISCARD` | 過於情境特定或 rationale-only | GC 並記錄原因（見下） |

---

#### Phase 2：落點與知識模式

分類為 `PROMOTE` 後，判斷知識模式，對應目標檔案：

| 知識模式 | 定義 | 目標檔案 |
|----------|------|----------|
| **A. 觸發式約束** | 「當 X 情況出現時，做/不做 Y」 | `rules/axioms/` 或 skill guardrails |
| **B. 環境事實** | 「系統的 X 是 Y，不需要推測」 | `rules/ENVIRONMENT.md` |
| **C. 設計原則** | 「做 X 類決策時，優先考慮 Y 而非 Z」 | `rules/COMMUNICATION.md` Agentic Principles 或 `rules/skills/` 設計指南 |
| **不確定** | 無法明確歸類 | 預設放 `rules/axioms/`（最中性的 fallback） |

---

#### Purpose Statement + Reader Test（各目標檔案）

| 目標檔案 | Purpose Statement | Reader Test |
|----------|-------------------|-------------|
| `SOUL.md` | AI agent 的身份認同與邊界原則 | 「AI 讀完後，面對模糊要求時知道自己是誰、該如何自我定位嗎？」 |
| `USER.md` | 使用者的背景、偏好與溝通風格 | 「AI 讀完後，能調整回應風格以符合使用者的預期嗎？」 |
| `ENVIRONMENT.md` | 環境基底事實（設備、帳號、工具） | 「AI 讀完後，對環境的假設能正確嗎？不需要額外推測嗎？」 |
| `COMMUNICATION.md` | AI 互動原則與非程式任務框架 | 「AI 讀完後，在 agentic 任務中知道該如何決策和溝通嗎？」 |
| `WORKSPACE.md` | 目錄路由與工作區慣例 | 「AI 讀完後，知道任何類型的內容/工具該放哪、去哪找嗎？」 |
| `rules/axioms/` | 觸發式約束，遇到特定情境時的行動規則 | 「AI 讀完後，在觸發條件出現時能直接執行行動嗎？」 |
| `rules/skills/` | 特定能力的執行 SOP 與 guardrails | 「AI 讀完後，能正確執行這項能力且避免已知錯誤嗎？」 |

若某條知識無法自然符合任何 Reader Test，優先使用 `rules/axioms/` 作為 fallback，而非強行放入語意不符的檔案。若發現某檔案的 Reader Test 已不準確，應優先更新此 Purpose Map 再晉升。

---

#### 有理由的 GC（Justified GC）

任何被 GC 的 🔴 High 觀測，MUST 在彙報中標記不晉升原因：

| 標籤 | 含義 |
|------|------|
| `already-derivable` | 可從當前 rules/ 或系統結構直接推導 |
| `rationale-only` | 只是設計理由，不含行動指令 |
| `one-time-event` | 只出現一次，留 `NOT_YET` 更適合 |
| `promoted` | 已晉升（應標記目標檔案路徑） |

---

#### 內容轉換：觀測 → 行動指令

晉升時 MUST 將觀測文字（過去式事件記錄）改寫為行動指令（現在式可操作規則）。

- **禁止**：直接複製貼上觀測文字（如「確認了 X 機制」「發現 Y 問題」）
- **要求**：改寫為 AI 可直接執行的指令（如「使用 X 時，先檢查 Y」「遇到 Z 情況時，執行 W」）

## 5. 執行角色隔離 (Role Isolation)
- **Observer (L1)** 和 **Reflector (L2)** 是獨立的任務階段。
- 在執行 **Observer** 任務時，模型應聚焦於“記錄”，不要主動修改 `rules/` 目錄。
- 這種隔離是為了防止在觀測階段引入未經人類確認的規則變動。

## 6. 專案 Staleness 驗證 (Project Freshness Check)

### 6.1 掃描目標

每次 Observer 執行時，額外掃描 `projects/INDEX.md`，識別 status 為 `active` 但 `last_updated` 超過閾值的專案。

### 6.2 過時判斷邏輯

```python
# 讀取 projects/INDEX.md，解析 table 中每一行
# 格式（table columns）：name | status | last_updated | description
# 僅篩選 status == "active" 的行；paused / completed / archived 一律跳過
# 若 (today - last_updated) > staleness_threshold_days（預設 14）→ 觸發警示
```

步驟：
1. 讀取 `projects/INDEX.md`
2. 解析 markdown table，取得每個專案的 name、status、last_updated
3. 篩選 status 為 `active` 的專案（`paused`、`completed`、`archived` 狀態一律跳過，不觸發 staleness 警告）
4. 計算距今天數；超過 `staleness_threshold_days`（預設 14）則標記為過時
5. 對每個過時條目，在 `memory/OBSERVATIONS.md` 末尾追加一條 🟡 Medium 觀測

### 6.3 觀測記錄格式

```
🟡 [State] `projects/INDEX.md` 中「<name>」已 <N> 天未更新（last_updated：YYYY-MM-DD），請確認是否仍為 active
```

### 6.4 注意事項

- 此檢查是「提醒」而非「自動刪除」——不修改 projects/INDEX.md，只寫觀測
- 若 projects/INDEX.md 不存在，跳過此步驟並記錄一條 🟢 Low 觀測說明檔案缺失
- staleness_threshold_days 預設為 14，可於未來在 projects/INDEX.md frontmatter 中自訂

---

## 7. 回報機制 (Reporting)
- 在完成檔案寫入後，你只需在 Chat 中給出一個簡短的 Summary（Walkthrough）。
- **Observer 彙報點**: 處理了哪些專案，基於 Metadata 過濾掉了多少噪音；以及 state/active.md 的驗證結果（幾個條目過時）。
- **Reflector 彙報點**: 哪些觀測點變成了正式規則。

---

## 8. 個人事實提取 SOP (PersonalFacts Extraction)

### 8.1 適用範圍（Observer 執行）

掃描以下目錄中近期新增或修改的文件（`find -mtime -1` 範圍內），讀取文件內容並提取個人環境事實：

- `contexts/survey_sessions/`
- `contexts/thought_review/`

### 8.2 個人事實的定義

以下類別算作個人事實，應提取：

- **設備 / 硬體**：機器名稱、型號、用途（例：MacBook Pro 公司機、Mac mini 家用機）
- **帳號架構**：各平台的帳號配置、隔離規則（例：每台機器只登一個 Claude Code 帳號）
- **工具與連線**：主要使用的軟體工具、連線方式、設定（例：Cursor + Remote SSH、Tailscale）
- **工作流限制**：硬性約束或不可違反的操作規則（例：禁止在同一台機器切換帳號）

以下**不算**個人事實，不應提取至 PersonalFacts：

- 方法論、工作原則、思考框架（→ 由 Reflector 提升至 `rules/` 其他檔案）
- 專案進展、技術決策、任務完成狀態（→ 寫入一般觀測條目）
- 單次 debug 記錄、臨時上下文

### 8.3 PersonalFacts 觀測格式

```
🟡 [PersonalFacts] 來源：contexts/survey_sessions/xxx.md
  - 設備：[Work machine]（work）、[Home machine]（home）
  - 帳號架構：每台機器單一 Claude Code 帳號，禁止切換
  - 工具：[IDE + Remote SSH] 作為主工作介面
  - 連線：[VPN solution] 虛擬內網
```

規則：
- 標籤必須為 `[PersonalFacts]`（大小寫一致）
- 來源路徑使用相對於根目錄的完整路徑
- 每個事實一行，前綴類別名稱

### 8.4 Reflector 對 PersonalFacts 的處理

1. 讀取 OBSERVATIONS.md，識別所有標籤以 `[PersonalFacts` 或 `[個人事實` 開頭的條目（Observer 可能使用英文或中文標籤）
2. 將條目內的事實 **merge** 寫入 `rules/ENVIRONMENT.md` 對應類別區塊
3. 相同類別的舊事實被新事實**覆蓋**（不保留矛盾的舊條目）
4. 完成後將已處理的條目納入 GC 範圍（可刪除）

---

## 9. OpenSpec 歸檔掃描 (OpenSpec Archive Scanning)

### 9.1 掃描目標

每次 Observer 執行時，掃描 `openspec/changes/archive/` 目錄，識別當天完成歸檔的 OpenSpec changes。

### 9.2 掃描方法

```bash
# 列出歸檔目錄，篩出前綴符合 target_date 的子目錄
ls openspec/changes/archive/ | grep "^{target_date}-"
```

- `target_date` 格式為 `YYYY-MM-DD`（即 observer 執行的目標日期）
- 歸檔目錄命名格式為 `YYYY-MM-DD-<name>`，前綴即歸檔日期
- 若無符合項目，跳過本節，不產生任何觀察條目

### 9.3 觀察條目格式

對每個符合的歸檔目錄：

1. 讀取 `proposal.md`，提取 What Changes、Capabilities 段落
2. 讀取 `design.md`，提取 Decisions 區塊的關鍵技術決策
3. 讀取 `devlog.md`（若存在），提取「踩過的坑」與「可提煉的經驗」兩個 section

觀察條目格式：

```
{emoji} [OpenSpec] 架構變更完成：{change-name}
  - 變更：{proposal.md 的 What Changes 摘要}
  - 能力：{proposal.md 的 Capabilities 摘要}
  - 決策：{design.md 的 Decisions 關鍵決策}
  - 踩坑：{devlog.md 的「踩過的坑」摘要}（僅在 devlog.md 存在時輸出）
  - 經驗：{devlog.md 的「可提煉的經驗」摘要}（僅在 devlog.md 存在時輸出）
```

其中 `{change-name}` 為目錄名去除日期前綴後的部分（例：`2026-04-04-add-observer-openspec-scanner` → `add-observer-openspec-scanner`）。

### 9.4 優先級判斷

優先級由 observer 依 §3.1 語意規則，綜合 proposal.md 與 design.md 的內容自行判斷，不預設固定值。

判斷參考：
- 跨模組架構重構、核心規則變更、具跨專案通用價值的方法論決策 → 🔴 High
- 新增功能、局部模組調整、活躍專案里程碑 → 🟡 Medium
- 小型 SOP 調整、文件更新 → 🟢 Low

### 9.5 Fallback 規則

- **proposal.md 不存在**：記錄一條 🟢 Low 觀察說明該歸檔目錄缺少 `proposal.md`，繼續處理其他條目，不中斷
- **design.md 不存在**：僅從 `proposal.md` 提取變更摘要，觀察條目中不包含技術決策段落，不中斷
- **devlog.md 不存在**：正常產生觀察條目，僅略過踩坑/經驗段落，不中斷、不報錯
