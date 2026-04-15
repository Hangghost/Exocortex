## ADDED Requirements

### Requirement: Stage 1 — Haiku Triage（分診）

系統 SHALL 使用 Haiku 4.5 透過 Anthropic Raw API Batch 模式，對 `raw_signals/<date>/` 下所有 `triage: null` 的信號進行分診，並將結果標記為 `"high"` / `"uncertain"` / `"noise"`。Batch 請求 MUST 帶有 Prompt Cache 標頭（`cache_control`）於 system prompt，以重用 persona context。

Stage 1 SHALL 作為 `capture.py` pipeline 的一部分執行，不再透過 `main.py` 觸發。

#### Scenario: 高相關性信號的識別

- **WHEN** 信號內容與使用者的活躍專案（projects/INDEX.md）、技術興趣或當前工作脈絡高度相關
- **THEN** Stage 1 將該信號的 `triage` 標記為 `"high"`

#### Scenario: 不確定信號的識別

- **WHEN** 信號無法明確判斷相關性（如：通用型會議標題、模糊的 commit message）
- **THEN** Stage 1 將該信號的 `triage` 標記為 `"uncertain"`，進入 Stage 2 二次判斷

#### Scenario: 明顯雜訊的識別

- **WHEN** 信號明確屬於雜訊（如：newsletter、routine 系統通知、無關領域的 Email）
- **THEN** Stage 1 將該信號的 `triage` 標記為 `"noise"`，移入 30 天 raw archive

#### Scenario: Batch 請求送出

- **WHEN** Stage 1 對一批信號發起處理
- **THEN** 所有信號 MUST 打包為單一 Batch API 請求，system prompt 使用 `cache_control` 標記以啟用 Prompt Cache

---

### Requirement: Stage 2 — Sonnet 二次判斷

系統 SHALL 使用 Sonnet 4.6 透過 Anthropic Raw API，對 Stage 1 標記為 `"uncertain"` 的信號進行二次判斷，產出 `"high"` 或 `"noise"` 的最終分類。Stage 2 的 system prompt MUST 包含 `projects/INDEX.md` 的文字摘要作為額外上下文，並使用 Prompt Cache。

Stage 2 SHALL 作為 `capture.py` pipeline 的一部分執行，不再透過 `main.py` 觸發。

#### Scenario: Uncertain 信號升級為 High

- **WHEN** Stage 2 判斷某 uncertain 信號與使用者活躍專案或技術脈絡有關聯
- **THEN** 將該信號 `triage` 更新為 `"high"`

#### Scenario: Uncertain 信號確認為 Noise

- **WHEN** Stage 2 判斷某 uncertain 信號確實與使用者無關
- **THEN** 將該信號 `triage` 更新為 `"noise"`，移入 30 天 raw archive

#### Scenario: Stage 2 不處理非 uncertain 信號

- **WHEN** Stage 2 執行時遇到 `triage` 為 `"high"` 或 `"noise"` 的信號
- **THEN** 跳過該信號，不重新判斷

---

### Requirement: Noise 信號的 Raw Archive 與 GC

系統 SHALL 將所有 `triage: "noise"` 的信號移入 `raw_signals/archive/<date>/`，並在 30 天後自動刪除。Archive 目錄 MUST 同樣被 `.gitignore` 排除。

Archive 與 GC SHALL 作為 `capture.py` pipeline 的最後步驟執行，不再透過 `main.py` 觸發。

#### Scenario: Noise 信號移入 Archive

- **WHEN** Stage 1 或 Stage 2 將信號標記為 `"noise"`
- **THEN** 該信號 JSON 移入 `raw_signals/archive/<capture_date>/`，不立即刪除

#### Scenario: 30 天後自動 GC

- **WHEN** capture.py 執行，發現 `raw_signals/archive/` 下存在超過 30 天的子目錄
- **THEN** 自動刪除該子目錄及其所有檔案，並記錄 GC 條數
