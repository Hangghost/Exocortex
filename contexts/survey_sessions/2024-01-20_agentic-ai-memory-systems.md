---
date: 2024-01-20
topic: Agentic AI 記憶系統設計模式
tags: [ai, memory, agentic, architecture]
l0: 研究 AI agent 記憶系統設計模式，比較主流方案
---

# Survey: Agentic AI 記憶系統設計模式

> **NOTE:** This is an example file demonstrating the survey_session format.
> Replace with your actual research sessions.

## 研究動機

在設計 Exocortex 的記憶架構之前，需要了解現有方案的設計選擇和取捨，避免重複造輪子，也避免犯同樣的錯誤。

## 主要發現

### 1. 向量資料庫方案（Mem0, Weaviate）

**優點:**
- 語義搜尋能力強
- 可以跨大量文件快速找到相關記憶

**缺點:**
- 黑盒，難以手動審計和修正
- 需要額外服務，部署複雜
- 記憶的「晉升」和「遺忘」邏輯不透明

### 2. 結構化記憶方案（MemGPT, Langchain Memory）

**優點:**
- 有明確的記憶類型（工作記憶、長期記憶）
- 可程式化控制

**缺點:**
- 通常與特定 LLM 框架緊密耦合
- 缺乏人類可讀的審計介面

### 3. 純檔案系統方案（本系統採用）

**優點:**
- 完全透明，任何文字編輯器都可以讀寫
- git 提供版本控制和審計歷史
- 不鎖定在特定 AI 平台或向量資料庫

**缺點:**
- 語義搜尋需要額外腳本（`infra/tools/semantic_search/`）
- 規模較大時索引速度可能成為瓶頸

## 關鍵設計決策

**選擇純檔案系統方案**，理由：
1. 可移植性最高：換工具不需要遷移資料
2. 人類可審計：任何時候都可以手動檢查和修正記憶
3. 組合彈性：可以在檔案系統上疊加向量索引（不是非此即彼）

## 參考資源

- [MemGPT Paper](https://arxiv.org/abs/2310.08560)
- [Building a Second Brain (Tiago Forte)](https://www.buildingasecondbrain.com/)
- Cognitive science: episodic vs semantic memory distinctions
