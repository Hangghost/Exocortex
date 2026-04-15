---
name: create-skill
description: >
  System-specific guide for adding a new skill to this repo's rules/skills/ layer.
  Covers directory structure, frontmatter format, INDEX.md sync via sync-skill-index.py,
  and sensitive config file handling. Use when: adding a new system skill, not a
  user-level (~/.claude/skills/) skill (use skill-creator for that).
---

# create-skill

Guide for adding a new system skill to `rules/skills/` in this repository.

---

## When to Use This Skill

Use this skill when adding a **system-level skill** — one that belongs in `rules/skills/` because it encodes repo-specific knowledge that any agent (Cursor, OpenCode, Claude Code) should be able to discover.

For **user-level** skills (`~/.claude/skills/`), use the `skill-creator` skill instead.

---

## Interactive Flow

### Step 1 — Collect details

Ask the user for the following in a single question:

1. **Name** (kebab-case, e.g. `my-skill`) — this becomes the directory name and frontmatter `name`
2. **Description** — one short paragraph that fits in a single `description:` YAML field; will appear in INDEX.md
3. **Does this skill need a `scripts/` subdirectory?** (yes/no) — if yes, also ask what Python packages are required
4. **Does this skill need a `references/` subdirectory?** (yes/no)

5. **Does this skill include or require an associated slash command?** (yes/no) — if yes, also ask which namespace it belongs to (see Step 1.5 below)

Confirm the collected values with the user before creating any files.

#### Step 1.5 — Namespace assessment (if a command is associated)

If the skill includes a slash command, ask the user to confirm the namespace:

> Which namespace does this command belong to?
> - `ctx:` — architecture development tools (project context, git workflows, arch experiments)
> - `opsx:` — OpenSpec design workflow tools (propose, apply, archive)
> - `think:` — daily thinking aids used while working within the framework (eval, review)
> - No namespace — cross-repo general utility (goes in `~/.claude/commands/`)

Record the rationale in the SKILL.md body (e.g., "placed under `think:` because it's a judgment/evaluation tool used ad-hoc during daily work, not tied to a specific workflow phase").

**UX 原則**：確認應發生在語義層而非執行層。若執行環境已有安全門（如 Bash 確認），Skill 層不應重複；應用 flag（如 `--push`）讓呼叫者明確授權，而非在執行流程中詢問。

### Step 2 — Create directory structure

```
rules/skills/<name>/
  SKILL.md
  scripts/          (if requested)
  references/       (if requested)
```

Do NOT create a `scripts/.env` file — it is covered by `.gitignore`.

### Step 3 — Write SKILL.md

Create `rules/skills/<name>/SKILL.md` with this structure:

```markdown
---
name: <name>
description: >
  <description>
---

# <Name>

<Body — document the skill's workflow, scripts reference, usage examples, etc.>
```

**Frontmatter rules:**
- `name`: exact kebab-case directory name
- `description`: YAML block scalar (`>`), first line blank after `>`, content indented 2 spaces
- No other required frontmatter fields

### Step 4 — Register dependencies (if scripts/ exists)

If the skill has scripts with Python dependencies, add a dependency group to `pyproject.toml`:

```toml
[dependency-groups]
<name> = [
    "some-package>=1.0.0",
]
```

Then install:

```bash
uv sync --all-groups
```

If there are no script dependencies, skip this step.

### Step 5 — Sync INDEX.md

After creating the SKILL.md, run:

```bash
uv run infra/tools/sync-skill-index.py
```

This scans all `rules/skills/*/SKILL.md` files and rebuilds `rules/skills/INDEX.md` from their frontmatter. No manual INDEX.md editing required.

### Step 6 — Sensitive config handling (if scripts/ exists)

If the skill uses scripts that need credentials or environment-specific config:

- **Do not store secrets in `scripts/.env`** — this file is covered by `.gitignore` (`rules/skills/**/scripts/.env`), so it will never be committed, but it also won't be available to other users.
- **Store config at `~/.config/<skill-name>/`** — use a `config.json` for paths and a separate `credentials.json` or similar for secrets outside the repo.
- Document the expected config schema in the SKILL.md body.
- Provide an `accounts.example.json` or similar template file (without real credentials) that users can copy.

---

## Checklist

- [ ] `name` is kebab-case and matches the directory name
- [ ] `description` fits in one short paragraph and is meaningful in INDEX.md
- [ ] SKILL.md frontmatter is valid YAML
- [ ] If scripts/: dependency group added to `pyproject.toml` and `uv sync --all-groups` run
- [ ] `infra/tools/sync-skill-index.py` was run and INDEX.md updated
- [ ] No credentials or `.env` files committed

---

## Reference

- INDEX.md: `rules/skills/INDEX.md`
- Sync script: `infra/tools/sync-skill-index.py`
- Example skill: `rules/skills/ec2-deploy/SKILL.md`
