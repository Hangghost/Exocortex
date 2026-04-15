# Skills Index

系統 skills 的能力速查入口。Session 啟動時被動載入此索引（metadata only）；需要執行某項能力時，再讀取對應的完整 `SKILL.md`。

**系統 skills**（本索引，`rules/skills/`）與 **agent-specific skills**（如 `.claude/skills/`）互補，合併為本次 session 的完整能力圖。

---

## 系統 Skills

| Name | Description | 路徑 |
|------|-------------|------|
| create-skill | System-specific guide for adding a new skill to this repo's rules/skills/ layer. Covers directory structure, frontmatter format, INDEX.md sync via sync-skill-index.py, and sensitive config file handling. Use when: adding a new system skill, not a user-level (~/.claude/skills/) skill (use skill-creator for that). | `rules/skills/create-skill/SKILL.md` |
| obsidian | Obsidian vault interaction skill. Read, write, create, list, move, search notes and update YAML frontmatter via CLI scripts. Supports two access modes: Obsidian Local REST API (primary, when plugin is running) and direct filesystem (fallback). Includes an AI-driven organizer workflow: analyze a folder, propose a reorganization plan, and execute batch moves + frontmatter updates + index note creation. Use when: reading/writing Obsidian notes, searching the vault, auto-organizing a folder, or updating note properties. | `rules/skills/obsidian/SKILL.md` |
| ec2-deploy | EC2 部署最佳實踐與常見坑。涵蓋記憶體吃緊時的 deploy-local 策略（本機 build 再傳 image）、Elastic IP 設定、Ghost CMS headless 架構的 proxy/routes.yaml/X-Forwarded-Proto 陷阱、Next.js OG metadataBase 設定、跨機器部署（SSH key 分離）。Use when: 部署 Next.js 或 Ghost 到 EC2、遇到 OOM/IP 變更/Docker 部署問題。 | `rules/skills/ec2-deploy/SKILL.md` |

---

*每新增或刪除一個 skill，請同步更新本表格。可執行 `tools/sync-skill-index.py` 自動重建。*
