---
date: 2024-01-25
type: reflection
topic: AI-native 工具設計哲學
l0: 反思 AI-native 工具設計，核心：工具應適應 AI 工作流而非反之
---

# 覆盤：AI-native 工具設計哲學

> **NOTE:** This is an example file demonstrating the thought_review format.
> Replace with your actual reflections and retrospectives.

## 觸發點

在設計 Exocortex 架構時，不斷遇到一個核心問題：「這個設計是為了讓人類方便，還是為了讓 AI agent 方便？」兩者往往衝突。

## 核心洞察

### 1. AI-native ≠ 人類不可讀

一個常見的誤解：為 AI 設計的系統應該是機器格式（JSON、XML、向量）。實際上，**Markdown + 清晰的結構就是 AI 最友好的格式**，因為：
- LLM 在 Markdown 上訓練了大量資料
- 人類可以直接閱讀和編輯，形成快速反饋循環
- 結構化的 Markdown（frontmatter + heading hierarchy）可以被解析也可以被語義理解

### 2. 工具應適應 AI 工作流，而非反之

傳統工具假設「人類是主要操作者」。AI-native 工具假設「AI 是主要操作者，人類是審計者和決策者」。這意味著：
- 讀取路徑要清晰（AI 應該能在 3 個 hop 內找到任何資訊）
- 寫入結構要一致（AI 輸出可以被程式化處理）
- 邊界要明確（哪些目錄是 AI 輸入，哪些是 AI 輸出）

### 3. 漸進式揭露的重要性

不要在 session 開始時就把所有 context 塞進去。設計 L0 一行摘要（`l0:` frontmatter 欄位），讓 AI 先掃描相關性，再深入讀取。這是 token 預算管理的基本原則。

## 可提煉的原則

- **Principle:** 設計給 AI 讀的文件，應該既讓 AI 能快速掃描相關性，又讓人類能直接理解和修改。
- **Trigger:** 當設計新的資料格式或目錄結構時觸發。

## 下一步

將這些原則形式化為 Axioms，加入 `rules/axioms/`。
