---
name: web-clip
description: >
  Clip web articles into Markdown + images for blog reference. Downloads article
  content, saves as structured Markdown with optional Traditional Chinese translation.
  Use when user invokes /clip with a URL.
---

# web-clip

將網頁文章儲存為 Markdown + 圖片，供部落格寫作參考使用。

## 觸發方式

使用者執行 `/clip <URL>` 或明確要求剪輯某篇文章時觸發。

## 實作位置

- **User-level skill**：`~/.claude/skills/web-clip/SKILL.md`
- **執行腳本**：`/Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills/skills/web-clip/scripts/clip.py`

## 工作流程

1. 詢問輸出路徑（預設：`~/Documents/Procjects/00_work_space/brain/clips`，或自訂）
2. 執行 clip.py，傳入 URL 與選項
3. 顯示儲存路徑與輸出結構

## 腳本選項

```bash
# 基本剪輯（不翻譯）
uv run python skills/web-clip/scripts/clip.py "<url>"

# 加入英→繁中翻譯（預設用 claude-haiku-4-5）
uv run python skills/web-clip/scripts/clip.py "<url>" --translate

# 指定翻譯 API：openai / gemini / grok
uv run python skills/web-clip/scripts/clip.py "<url>" --translate --api openai

# 自訂輸出目錄
uv run python skills/web-clip/scripts/clip.py "<url>" --output-dir "/path/to/dir"
```

所有指令須在 `/Users/chenhunglun/Documents/Procjects/LearningHacker-claude-skills` 目錄下執行。

## 常見錯誤

- **無法擷取內容**：該網站可能封鎖爬蟲或結構特殊
- **Network error**：請確認網路連線
- **Missing API key**：使用 `--translate` 時需設定對應的環境變數
