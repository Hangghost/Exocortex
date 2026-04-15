---
name: ctx:arch
description: 架構變更工作流入口。討論方案，產出 OpenSpec proposal，開分支。
---

架構變更工作流入口。用於修改 `rules/`、`AGENTS.md`、`CLAUDE.md` 或任何影響 AI 行為的設定。

**Input**: `$ARGUMENTS`
- 空白 → 進入討論模式（預設）
- 描述（例如 `新增 work logs 路由`）→ 作為討論的起點

---

## 互斥檢查

執行前先檢查工作區狀態：

```bash
git status --short
```

如果偵測到大量非架構檔案的變更（`contexts/`、`adhoc_jobs/`、`periodic_jobs/` 下的內容），提醒使用者考慮先用 `/ctx:content` 處理這些變更，避免 commit 邊界模糊。詢問是否繼續。

---

## Step 1 — 探索意圖與影響範圍

先讀 `rules/ARCHITECTURE.md` 了解全局架構（各區塊設計意圖、邊界與資料流），再開始探索。

執行：

```
使用 /opsx:explore 進行意圖釐清與影響範圍分析。
```

如果使用者已在訊息中說明意圖，將其作為 explore 的起點傳入。explore 結束並確認方案後，執行：

```
使用 /opsx:propose 產出 proposal、design、tasks 三份設計文件。
```

`opsx:propose` 完成後，根據 change name 開分支：

```bash
git checkout -b feature/<change-name>
```

> **架構異動提示**：若本次變更涉及**新增/刪除頂層目錄**或**改變資料流向**，在實作完成後需要更新 `rules/ARCHITECTURE.md`，以反映最新的系統結構。

---

## Step 2 — 告知下一步

開完分支後，提示使用者：

```
分支已建立：feature/<change-name>

設計文件在 openspec/changes/<change-name>/

建議開新 session 後繼續：
1. /opsx:apply      — 實作 tasks
2. /opsx:archive    — 歸檔設計文件
3. git commit       — 提交所有變更（包含 openspec/changes/archive/）
4. /ctx:merge       — 合併回 main
```

---

## Guardrails

- 本指令只負責討論與設計，不直接修改任何 rules/ 檔案
- 實作由 opsx:apply 負責，不在此執行
- 如果使用者想跳過討論直接進 opsx:propose，可接受，但要確認影響範圍已清楚
