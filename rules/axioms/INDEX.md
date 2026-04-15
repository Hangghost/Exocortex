# Axioms Index

從個人經歷中提煉的決策原則。這些不是通用的最佳實踐，而是「在這個人的具體情況下，哪條路更可能對」。
_Decision principles distilled from personal experience. Not generic best practices — these are "given this person's specific context, which path is more likely right."_

---

## 如何使用 / How to Use

- AI 在決策點（做 A 或做 B？）時觸發相關公理
- 每條公理有觸發詞（trigger）——當對話中出現這些詞時，AI 應主動應用對應公理
- 公理可以被新經歷覆蓋，這是系統健康的標誌

## 公理分類 / Axiom Categories

<!-- TODO: Add your axiom categories here.
     Suggested categories: Tech Decisions, Work Methodology, Learning, Communication, etc.
     Each category gets its own .md file in this directory. -->

| 分類 / Category | 描述 / Description | 觸發詞 / Triggers | 檔案 |
|----------------|-------------------|------------------|------|
| [example-tech] | Technology and architecture decisions | build, design, architecture | [example-tech.md](example-tech.md) |
| [example-work] | Work methodology and prioritization | priority, deadline, tradeoff | [example-work.md](example-work.md) |

---

## 示範公理 / Example Axioms

以下是示範格式。在 `exocortex-personal` 中，這些應替換為你的真實個人公理。

### [AXIOM-001] 系統 > 臨時方案

**觸發詞:** 「每次都要」「自動化」「反覆」「重複」

**原則:** 如果某件事重複超過 3 次，停下來設計系統而非繼續手動處理。臨時方案的技術債以指數速度累積。

**背景:** 花 30 分鐘設計一個系統，往往比花 5 分鐘重複做 10 次更划算。

---

### [AXIOM-002] 先理解，再解決

**觸發詞:** 「為什麼」「根本原因」「bug」「問題」

**原則:** 在找到根本原因之前，不要開始實作解決方案。症狀治療浪費時間且製造新問題。

**背景:** 快速修復的衝動往往導致 band-aid 解決方案，掩蓋真正的問題。

---

### [AXIOM-003] 明確的邊界勝過模糊的靈活性

**觸發詞:** 「要不要」「應該」「放在哪裡」「屬於」

**原則:** 當不確定某樣東西屬於哪裡時，定義清楚的規則並堅持。邊界一旦模糊，熵就開始累積。

**背景:** 「隨便放，以後再整理」是技術債的主要來源之一。

---

<!-- TODO: Replace the above examples with YOUR actual axioms.
     Format for each axiom:

     ### [AXIOM-NNN] Short Title

     **觸發詞:** keyword1, keyword2

     **原則:** The principle in 1-2 sentences.

     **背景:** Why this matters to you specifically.
-->
