# library/ — 個人 Library 使用指南

AI-agent native 的個人文件索引。只在 git repo 中存放 markdown index cards（摘要、標籤、路徑），binary 本體存放於 `~/Documents/AILibrary/`。

---

## Index Card 格式

每個 card 是一個獨立的 markdown 檔案，命名規則：`YYYY-MM-DD_<slug>.md`

```markdown
---
title: <文章標題或文件名稱>
type: article | document | resume | reference
date_saved: YYYY-MM-DD
tags: [tag1, tag2]
source_url: <若為文章，原始網址>
file_path: ~/Documents/AILibrary/<filename>  # 若有 binary
---

## 摘要
<1-3 句，AI 可快速判斷相關性>

## 標籤與關鍵字
<可被 grep 到的關鍵概念>
```

---

## 新增 Card 流程

1. 將 binary（PDF、影片等）放至 `~/Documents/AILibrary/`
2. 在 `library/` 下建立對應的 card 檔案
3. 在 `library/INDEX.md` 的表格新增一行

---

## 類型說明

| type | 說明 |
|------|------|
| `article` | 網路文章、部落格、論文 |
| `document` | 規格書、說明書、報告 |
| `resume` | 履歷、CV 相關 |
| `reference` | 參考資料、查找表、cheatsheet |

---

## 與其他系統的關係

- **KnowledgeWiki**（`~/Documents/Projects/KnowledgeWiki/`）：存放主動整理的領域知識概念，與 library/ 互補。library/ 偏向「個人珍藏的原始文件」，KnowledgeWiki 偏向「提煉後的領域知識」。
- **registry/library.md**：跨系統路由入口，AI 執行 library 相關任務前先查此檔。
