## ADDED Requirements

### Requirement: Experiment branch creation
The system SHALL create an isolated git branch named `experiment/<YYYY-MM-DD>-<name>` from the current `main` HEAD when user invokes `ctx:experiment start <name>`, and SHALL append a new row to `openspec/experiments/INDEX.md` (creating the file if it does not exist).

#### Scenario: Start a new experiment
- **WHEN** user runs `/ctx:experiment start test-survey-obs`
- **THEN** system creates branch `experiment/2026-04-06-test-survey-obs` from main HEAD
- **THEN** system appends a row to `openspec/experiments/INDEX.md` with date, branch name, purpose (derived from name), and status `in-progress`
- **THEN** system prints instructions for running observer/reflector manually

#### Scenario: Start with existing uncommitted changes
- **WHEN** user runs `/ctx:experiment start <name>` while on a non-main branch or with uncommitted changes
- **THEN** system warns the user and asks for confirmation before proceeding

### Requirement: Experiment diff display
The system SHALL display a formatted summary of changes between the experiment branch and `main` when user invokes `ctx:experiment diff`.

#### Scenario: Diff after running observer
- **WHEN** user runs `/ctx:experiment diff` on an experiment branch
- **THEN** system runs `git diff main...HEAD -- memory/OBSERVATIONS.md` and displays new observation entries
- **THEN** system runs `git diff main...HEAD -- rules/` and displays any rule changes
- **THEN** system shows a summary: N lines added to OBSERVATIONS.md, N files changed in rules/

#### Scenario: Diff with no changes
- **WHEN** user runs `/ctx:experiment diff` and no changes have been made since branch creation
- **THEN** system reports "No changes detected since branch creation"

### Requirement: Experiment promotion
The system SHALL update `openspec/experiments/INDEX.md` with the conclusion and status `promoted`, then prompt the user to run `/ctx:merge` when user invokes `ctx:experiment promote`.

#### Scenario: Promote an experiment
- **WHEN** user runs `/ctx:experiment promote` with an optional conclusion string
- **THEN** system updates the INDEX.md row for the current branch: status → `promoted`, conclusion → provided text (or prompts for one)
- **THEN** system prints: "Run `/ctx:merge` to merge this experiment into main"
- **THEN** system does NOT automatically merge

### Requirement: Experiment discard
The system SHALL update `openspec/experiments/INDEX.md` with the conclusion and status `discarded` when user invokes `ctx:experiment discard`. Branch deletion SHALL be opt-in via `--delete` flag.

#### Scenario: Discard and keep branch
- **WHEN** user runs `/ctx:experiment discard "需要再調整晉升門檻"` without `--delete`
- **THEN** system requires a conclusion (non-empty string)
- **THEN** system updates INDEX.md: status → `discarded`, conclusion → provided text
- **THEN** system checks out `main`
- **THEN** branch is preserved for future reference

#### Scenario: Discard and delete branch
- **WHEN** user runs `/ctx:experiment discard "效果不佳" --delete`
- **THEN** system updates INDEX.md and checks out main
- **THEN** system runs `git branch -D experiment/<name>` to delete the branch

### Requirement: Experiment index initialization
The system SHALL create `openspec/experiments/INDEX.md` with a header and empty table if the file does not exist when any experiment operation writes to it.

#### Scenario: First experiment ever
- **WHEN** `openspec/experiments/INDEX.md` does not exist and user runs `/ctx:experiment start <name>`
- **THEN** system creates `openspec/experiments/` if needed, creates `INDEX.md` with the standard header and table structure, then appends the first row
