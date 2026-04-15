---
date: 2024-01-15
project: exocortex
type: work_log
l0: 示範工作記錄：設計三層記憶架構
---

# Work Log: 三層記憶架構設計

> **NOTE:** This is an example file demonstrating the work_log format.
> Replace with your actual work logs.

## 今日目標

設計並實作 Exocortex 三層記憶架構的核心 schema：
- L3 (Rules): 跨 session 永久規則層
- L1/L2 (Observations): 短期到中期觀測層
- L0 (Raw Signals): 每日捕獲的原始訊號

## 過程記錄

**10:00** 研究現有 second-brain 系統的記憶架構。PKM 工具（Obsidian、Logseq）主要服務人類讀者，而非 AI agent。現有 AI 記憶方案（Mem0、MemGPT）過於黑盒，無法手動審計。

**11:30** 確定設計方向：檔案系統作為記憶基底，git 作為版本控制，Markdown 作為通用格式。這確保任何工具都可以讀寫，不鎖定在特定 AI 平台。

**14:00** 完成 WORKSPACE.md 路由規則草稿：
- `rules/`: L3 永久規則（AI 每 session 讀取）
- `contexts/`: L1 短期行為記錄（observer 掃描）
- `memory/`: L2 中期觀測（reflector 晉升）

**16:00** 設計 observer 的掃描 schema（`contexts/MANIFEST.md`），確保不同子資料夾有不同的處理邏輯。

## 產出

- `rules/WORKSPACE.md`（v1 草稿）
- `contexts/MANIFEST.md`（observer schema）
- 架構決策：不使用向量資料庫，改用語義搜尋腳本（portable, auditable）

## 遺留問題

- Reflector 的晉升策略尚未明確：什麼樣的 observation 值得進入 rules/?
- PersonalFacts 提取的粒度：應該多細？

## 明日計畫

實作 v0 Observer，驗證掃描邏輯是否符合 MANIFEST 設計。
