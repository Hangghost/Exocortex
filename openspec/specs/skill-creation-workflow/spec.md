### Requirement: create-skill guides end-to-end skill creation in this system
`rules/skills/create-skill/` SHALL provide a SKILL.md that guides an agent through the complete process of adding a new system skill to this repo, covering directory structure, frontmatter, INDEX.md sync, and sensitive file handling.

#### Scenario: Agent creates a valid system skill
- **WHEN** agent invokes the `create-skill` skill to create a new skill named `foo-bar`
- **THEN** a directory `rules/skills/foo-bar/` is created with a valid `SKILL.md` containing `name: foo-bar` and a non-empty `description`

#### Scenario: INDEX.md is updated after skill creation
- **WHEN** agent completes the create-skill workflow
- **THEN** `infra/tools/sync-skill-index.py` is called and `rules/skills/INDEX.md` reflects the new skill's name and description

#### Scenario: Sensitive config files are kept out of repo
- **WHEN** a new skill requires user-specific config (e.g., API credentials path)
- **THEN** agent is guided to store config at `~/.config/<skill-name>/` and the skill's `scripts/.env` is covered by `.gitignore`

#### Scenario: Workflow confirms details before creating
- **WHEN** agent invokes create-skill
- **THEN** agent collects at minimum `name` and `description` and confirms with user before creating any files

#### Scenario: 新增 command 時評估命名空間歸屬
- **WHEN** the new skill includes or requires an associated slash command
- **THEN** agent SHALL ask: which namespace does this command belong to — `ctx:` (architecture dev), `opsx:` (design workflow), `think:` (daily thinking aid), or no namespace (global utility) — and record the rationale in the skill documentation

### Requirement: sync-skill-index script rebuilds INDEX.md from frontmatter
`infra/tools/sync-skill-index.py` SHALL scan all `rules/skills/*/SKILL.md` files, read the `name` and `description` frontmatter fields, and overwrite `rules/skills/INDEX.md` with a table reflecting the current state.

#### Scenario: Script regenerates correct INDEX.md
- **WHEN** `python infra/tools/sync-skill-index.py` is run
- **THEN** `rules/skills/INDEX.md` contains exactly one row per skill in `rules/skills/`, with name and description matching the SKILL.md frontmatter

#### Scenario: Script is idempotent
- **WHEN** `python infra/tools/sync-skill-index.py` is run twice in a row with no file changes
- **THEN** `rules/skills/INDEX.md` content is identical after both runs

#### Scenario: Deleted skill is removed from INDEX.md
- **WHEN** a skill directory is removed and `sync-skill-index.py` is run
- **THEN** that skill no longer appears in `rules/skills/INDEX.md`
