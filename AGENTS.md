# AGENTS.md - Your Workspace

Before anything else, read `rules/CORE.md`.

This folder is home. Treat it that way.

## Skills

**Skills** 是 AI 可複用的能力，包括工作流、API 指南、最佳實踐等。系統 skills 存放於 `rules/skills/`（repo 維護，跨 agent 可攜）；agent-specific skills（如 `.claude/skills/`）由各 agent 維護。兩者互補，合併為本次 session 的完整能力圖。

**重要：遇到"怎麼做 X"時，先查 skills 再查系統工具。** 搜尋順序：(1) 下方速查表 → (2) `rules/skills/INDEX.md` → (3) 系統工具。

**需要執行某項任務** → 先查 `rules/skills/INDEX.md` 找到對應的 skill  
**想新增新能力** → 在 `rules/skills/<name>/SKILL.md` 建立，更新 INDEX.md

### 常用 Skills 速查（以 INDEX.md 為準）

**工作紀錄** → `contexts/work_logs/`
- 任務執行過程、進度追蹤、產出記錄

## Axioms（公理）

從個人經歷提煉的決策原則，用於啟發深度思考。分類索引、使用指南和觸發詞見 `rules/axioms/INDEX.md`。
