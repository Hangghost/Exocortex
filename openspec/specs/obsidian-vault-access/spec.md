## ADDED Requirements

### Requirement: Config loading with interactive fallback
The skill SHALL read vault configuration from `~/.config/obsidian/config.json`. If the file does not exist or required fields are missing, the skill MUST prompt the user to provide the missing values and persist them to config before proceeding.

#### Scenario: Config exists and is valid
- **WHEN** `~/.config/obsidian/config.json` exists with a valid `vault_path`
- **THEN** the skill proceeds using the configured vault path without prompting the user

#### Scenario: Config file is missing
- **WHEN** `~/.config/obsidian/config.json` does not exist
- **THEN** the skill prompts the user for `vault_path` and REST API settings, saves them to config, and continues

#### Scenario: vault_path in config no longer exists
- **WHEN** `vault_path` in config points to a directory that does not exist
- **THEN** the skill warns the user and re-prompts for the correct vault path before continuing

### Requirement: REST API mode with filesystem fallback
The skill SHALL attempt to use the Obsidian Local REST API for all operations. If the REST API is unavailable (Obsidian not running or plugin not configured), the skill MUST fall back to direct filesystem operations transparently.

#### Scenario: REST API available
- **WHEN** a GET request to the REST API root endpoint succeeds within 1 second
- **THEN** all operations use the REST API

#### Scenario: REST API unavailable
- **WHEN** a GET request to the REST API root endpoint times out or returns an error
- **THEN** all operations fall back to direct filesystem read/write on `vault_path`

### Requirement: Read note
The skill SHALL be able to read the full content of a note by path relative to vault root, returning both frontmatter properties and body content.

#### Scenario: Read existing note via REST API
- **WHEN** `obsidian.py read <relative-path>` is called and REST API is available
- **THEN** returns note content including frontmatter as structured data

#### Scenario: Read existing note via filesystem
- **WHEN** `obsidian.py read <relative-path>` is called and REST API is unavailable
- **THEN** reads the `.md` file directly and parses frontmatter with `python-frontmatter`

#### Scenario: Note does not exist
- **WHEN** the specified path does not exist in the vault
- **THEN** exits with code 1 and prints an error message to stderr

### Requirement: Write and create note
The skill SHALL be able to create a new note or overwrite an existing note at a specified path, with optional frontmatter properties.

#### Scenario: Create new note
- **WHEN** `obsidian.py write <relative-path> --content "..." --frontmatter '{"tags": ["ai"]}'` is called
- **THEN** creates the file (and any missing parent directories) with the specified content and frontmatter

#### Scenario: Overwrite existing note
- **WHEN** `obsidian.py write <relative-path>` is called on an existing note
- **THEN** replaces the file content; does not prompt for confirmation (caller's responsibility)

### Requirement: List notes in folder
The skill SHALL be able to list all `.md` files in a specified folder (non-recursive by default, recursive with flag).

#### Scenario: List folder contents
- **WHEN** `obsidian.py list <folder>` is called
- **THEN** returns a list of relative paths to all `.md` files in that folder

#### Scenario: Recursive list
- **WHEN** `obsidian.py list <folder> --recursive` is called
- **THEN** returns all `.md` files in the folder and all subfolders

### Requirement: Move and rename note
The skill SHALL be able to move a note to a new path within the vault.

#### Scenario: Move note via REST API
- **WHEN** `obsidian.py move <src> <dst>` is called and REST API is available
- **THEN** uses the REST API rename command to move the note (preserving backlinks if supported)

#### Scenario: Move note via filesystem
- **WHEN** `obsidian.py move <src> <dst>` is called in filesystem mode
- **THEN** moves the file using filesystem operations; logs a warning that backlinks are not updated

#### Scenario: Destination folder does not exist
- **WHEN** the destination parent folder does not exist
- **THEN** creates the parent folder(s) before moving

### Requirement: Update frontmatter properties
The skill SHALL be able to add, update, or remove YAML frontmatter properties in an existing note without altering the note body.

#### Scenario: Update tags on existing note
- **WHEN** `obsidian.py frontmatter <path> --set '{"tags": ["ai", "research"]}'` is called
- **THEN** merges the provided properties into the note's existing frontmatter and saves the file

#### Scenario: Remove a frontmatter property
- **WHEN** `obsidian.py frontmatter <path> --remove "status"` is called
- **THEN** removes the specified key from frontmatter if it exists

### Requirement: Search notes
The skill SHALL be able to search notes by keyword across the vault.

#### Scenario: Search via REST API
- **WHEN** `obsidian.py search <query>` is called and REST API is available
- **THEN** returns a list of matching note paths with relevant excerpts

#### Scenario: Search via filesystem
- **WHEN** `obsidian.py search <query>` is called in filesystem mode
- **THEN** performs a case-insensitive grep across all `.md` files and returns matching paths
