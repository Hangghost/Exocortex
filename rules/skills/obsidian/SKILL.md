---
name: obsidian
description: >
  Obsidian vault interaction skill. Read, write, create, list, move, search notes
  and update YAML frontmatter via CLI scripts. Supports two access modes:
  Obsidian Local REST API (primary, when plugin is running) and direct filesystem
  (fallback). Includes an AI-driven organizer workflow: analyze a folder, propose
  a reorganization plan, and execute batch moves + frontmatter updates + index
  note creation. Use when: reading/writing Obsidian notes, searching the vault,
  auto-organizing a folder, or updating note properties.
---

# Obsidian Skill

Interact with an Obsidian vault from AI agents.

---

## Setup Wizard (First Run)

**When this skill is invoked for the first time**, run through this setup:

### Step 1 — Check config

The scripts read `~/.config/obsidian/config.json`. If it doesn't exist, they will
interactively prompt for:
- `vault_path` — absolute path to the Obsidian vault folder
- `rest_api.api_key` — API key from the `obsidian-local-rest-api` plugin settings
  (leave blank to use filesystem-only mode)

To initialize manually, copy `scripts/config.example.json` to `~/.config/obsidian/config.json`
and fill in the values.

### Step 2 — Install the REST API plugin (optional, recommended)

In Obsidian → Settings → Community Plugins → search **Local REST API** → Install → Enable.
After enabling, go to plugin settings and copy the API key.

### Step 3 — Verify

```bash
uv run rules/skills/obsidian/scripts/obsidian.py list .
```

Expected output: JSON array of `.md` files in the vault root.

---

## Access Modes

| Mode | Trigger | Capabilities |
|------|---------|-------------|
| **REST API** | Plugin running, `api_key` set | All ops + search + (future) backlink-aware rename |
| **Filesystem** | Plugin unavailable or no key | All ops except full-text search (uses grep fallback) |

Mode is detected automatically on each script run (1s probe). No manual switching needed.

> **Warning**: If Obsidian is open and the file is written via filesystem while Obsidian has it
> open, sync conflicts may occur. Prefer REST API when Obsidian is running.

---

## Scripts Reference

Run all scripts via `uv run`. Scripts output JSON to stdout; errors to stderr with exit code 1.

### obsidian.py — Atomic vault operations

```bash
# Read a note (frontmatter + body)
uv run rules/skills/obsidian/scripts/obsidian.py read "folder/note.md"
# → {"frontmatter": {...}, "body": "..."}

# Create or overwrite a note
uv run rules/skills/obsidian/scripts/obsidian.py write "folder/note.md" \
  --content "Note body text" \
  --frontmatter '{"tags": ["ai", "research"], "status": "draft"}'

# List .md files in a folder
uv run rules/skills/obsidian/scripts/obsidian.py list "articles"
uv run rules/skills/obsidian/scripts/obsidian.py list "articles" --recursive

# Move / rename a note
uv run rules/skills/obsidian/scripts/obsidian.py move "inbox/idea.md" "projects/ai/idea.md"

# Update frontmatter without touching body
uv run rules/skills/obsidian/scripts/obsidian.py frontmatter "note.md" \
  --set '{"status": "done", "reviewed": true}'
uv run rules/skills/obsidian/scripts/obsidian.py frontmatter "note.md" --remove "draft"

# Search across vault
uv run rules/skills/obsidian/scripts/obsidian.py search "LLM agent"
# → [{"path": "...", "excerpt": "..."}, ...]
```

### organizer.py — AI-driven reorganization

```bash
# Step 1: Analyze a folder (AI uses this to plan reorganization)
uv run rules/skills/obsidian/scripts/organizer.py analyze "inbox"
# → JSON summary: [{path, title, tags, excerpt, word_count}, ...]

# Step 2: Preview planned operations (dry run)
uv run rules/skills/obsidian/scripts/organizer.py execute \
  --moves '[{"src": "inbox/idea.md", "dst": "projects/ai/idea.md"}]' \
  --frontmatter-updates '[{"path": "projects/ai/idea.md", "set": {"status": "active"}}]' \
  --create-index "projects/ai" --title "AI Projects" \
  --dry-run

# Step 3: Execute
uv run rules/skills/obsidian/scripts/organizer.py execute \
  --moves '[{"src": "inbox/idea.md", "dst": "projects/ai/idea.md"}]' \
  --frontmatter-updates '[{"path": "projects/ai/idea.md", "set": {"status": "active"}}]' \
  --create-index "projects/ai" --title "AI Projects"
```

---

## Auto-Organize Workflow

This is the recommended workflow when asked to "organize a folder":

1. **Analyze**: Run `organizer.py analyze <folder>` to get a JSON summary of all notes.
2. **Plan**: Read the summary and determine:
   - Which notes should be moved and where
   - Which frontmatter properties should be updated (e.g., tags, status)
   - Whether an index note (MOC) should be created
3. **Preview**: Show the plan to the user. Run `execute --dry-run` to print operations.
4. **Confirm**: Ask the user to confirm before executing (unless they've pre-authorized).
5. **Execute**: Run `execute` without `--dry-run` to apply changes.
6. **Report**: Show the result summary.

---

## Reference

- REST API endpoints → [references/rest_api.md](references/rest_api.md)
- Frontmatter properties and python-frontmatter usage → [references/frontmatter_guide.md](references/frontmatter_guide.md)

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `vault_path does not exist` | Config has wrong path | Re-run script; enter correct vault path when prompted, or edit `~/.config/obsidian/config.json` |
| `REST API unavailable — using filesystem mode` | Obsidian not running or plugin disabled | Normal — filesystem fallback is active. Start Obsidian + enable plugin for REST mode. |
| `401` from REST API | Wrong API key | Update `rest_api.api_key` in `~/.config/obsidian/config.json` |
| `note not found` | Path doesn't exist in vault | Check path is relative to vault root (e.g. `folder/note.md`, not absolute) |
| Sync conflicts after filesystem write | Obsidian had file open | Prefer REST API mode when Obsidian is running; close/reopen file in Obsidian |
| `--dry-run` shows no output | No operations passed | Provide at least one of `--moves`, `--frontmatter-updates`, or `--create-index` |
