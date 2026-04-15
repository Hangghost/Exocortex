## ADDED Requirements

### Requirement: Analyze folder for organization
The organizer SHALL be able to read all notes in a target folder, extract their content and frontmatter, and return a structured summary for the AI to analyze.

#### Scenario: Analyze folder with notes
- **WHEN** `organizer.py analyze <folder>` is called
- **THEN** returns a JSON summary of all notes including: path, title, tags, first 200 chars of body, and word count

#### Scenario: Empty folder
- **WHEN** the target folder contains no `.md` files
- **THEN** exits with code 0 and prints a message indicating no notes found

### Requirement: Show organization plan before executing
The organizer SHALL display a proposed reorganization plan and require explicit confirmation before making any changes.

#### Scenario: Plan presented to user
- **WHEN** the AI has determined a reorganization plan
- **THEN** `organizer.py plan` displays: files to move (src → dst), frontmatter updates (path, property, old → new value), and index notes to create

#### Scenario: User confirms plan
- **WHEN** the user confirms the plan
- **THEN** organizer executes all planned operations in sequence

#### Scenario: User rejects plan
- **WHEN** the user rejects or modifies the plan
- **THEN** organizer makes no changes and exits cleanly

### Requirement: Execute reorganization operations
The organizer SHALL be able to execute a batch of operations: move files, update frontmatter, and create index notes.

#### Scenario: Execute move operations
- **WHEN** `organizer.py execute --moves '[{"src": "...", "dst": "..."}]'` is called
- **THEN** moves each file using `obsidian.py move` and reports success/failure per file

#### Scenario: Execute frontmatter updates
- **WHEN** `organizer.py execute --frontmatter-updates '[{"path": "...", "set": {...}}]'` is called
- **THEN** updates frontmatter on each note using `obsidian.py frontmatter`

#### Scenario: Create index note (MOC)
- **WHEN** `organizer.py execute --create-index <folder> --title "..."` is called
- **THEN** generates a Map of Content note listing all notes in the folder with Obsidian `[[wikilink]]` format and writes it to `<folder>/index.md`

### Requirement: Dry-run mode
The organizer SHALL support a dry-run flag that prints all planned operations without executing them.

#### Scenario: Dry-run shows planned operations
- **WHEN** any `organizer.py execute` command is called with `--dry-run`
- **THEN** prints each operation that would be performed without making any file changes

### Requirement: Operation result reporting
The organizer SHALL report the outcome of each executed operation.

#### Scenario: All operations succeed
- **WHEN** all operations in a batch execute successfully
- **THEN** prints a summary: "X files moved, Y frontmatter updates, Z index notes created"

#### Scenario: Partial failure
- **WHEN** one or more operations fail during batch execution
- **THEN** continues with remaining operations, reports failures at the end with error details, and exits with code 1
