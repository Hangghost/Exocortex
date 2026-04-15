# OBSERVATIONS.md

Observer 的輸出落地點。每條觀察條目代表一個從 `contexts/` 掃描中提煉的訊號。

**這個檔案由 Observer 自動寫入，Reflector 定期提煉並晉升高價值條目到 `rules/`。**

---

## 格式規範

每條觀察條目的格式如下：

```markdown
### [YYYY-MM-DD] 觀察標題

**來源:** contexts/work_logs/2024-01-15_example.md
**信號強度:** 🔴 High / 🟡 Medium / 🟢 Low
**類型:** Progress / Decision / PersonalFact / Insight / Blocker

觀察內容（1-3 句話）。重點是 **what happened** 和 **why it matters**，
不是詳細過程記錄。

**晉升候選:** [是/否] — 若是，說明應晉升至哪個 rules/ 檔案及理由
```

---

## 觀察記錄

> **NOTE:** The entries below are examples demonstrating the format.
> Your actual OBSERVATIONS.md will be populated by the Observer pipeline.
> Delete these examples once you have real entries.

### [2024-01-15] 確定三層記憶架構設計方向

**來源:** contexts/work_logs/2024-01-15_example-work-log.md
**信號強度:** 🔴 High
**類型:** Decision

選擇純檔案系統（Markdown + git）而非向量資料庫作為記憶基底。核心理由：可移植性、人類可審計性、組合彈性。這是系統的基礎架構決策，影響所有後續設計。

**晉升候選:** 是 — 應在 ARCHITECTURE.md 中記錄此設計決策及其 rationale

---

### [2024-01-20] 識別 AI-native 工具設計原則

**來源:** contexts/thought_review/2024-01-25_on-building-ai-native-tools.md
**信號強度:** 🟡 Medium
**類型:** Insight

AI-native 工具的核心設計原則：Markdown 對 LLM 比機器格式更友好；漸進式揭露（L0 摘要先行）是 token 預算管理的關鍵；工具邊界（哪些是 AI 輸入 vs 輸出）必須明確。

**晉升候選:** 是 — 可提煉為 SOUL.md 的架構原則條目

---

### [2024-01-22] 發現 Observer 掃描的效率瓶頸

**來源:** contexts/work_logs/2024-01-22_observer-v0-testing.md
**信號強度:** 🟢 Low
**類型:** Blocker

v0 Observer 讀取所有 contexts/ 文件全文，在文件數量 >50 時 token 消耗過高。解決方向：引入 `l0:` frontmatter 欄位作為一行摘要，讓 Observer 先掃描 l0，再選擇性深入讀取。

**晉升候選:** 否 — 已在 SOUL.md 中記錄 L0/L1/L2 漸進式揭露原則

---
