# Obsidian Frontmatter Guide

Obsidian uses YAML frontmatter (between `---` delimiters) as note properties.

---

## Common Obsidian YAML Properties

| Property | Type | Description |
|----------|------|-------------|
| `tags` | list | Note tags. In Obsidian, tags can also be inline `#tag`. |
| `aliases` | list | Alternative names for the note (used by Obsidian link suggestions). |
| `cssclasses` | list | CSS classes applied to the note view. |
| `created` | string | ISO 8601 creation date (e.g. `2024-01-15`). |
| `modified` | string | ISO 8601 last-modified date. |
| `title` | string | Explicit title (overrides filename in some views). |
| `status` | string | Custom workflow status (e.g. `draft`, `done`, `archived`). |
| `source` | string | URL or reference for the note's source material. |
| `author` | string | Author attribution. |

### Example frontmatter block

```yaml
---
title: "LLM Agent Patterns"
tags:
  - ai
  - agents
  - research
aliases:
  - agent patterns
status: draft
created: "2024-01-15"
modified: "2024-03-20"
source: "https://example.com/paper"
---
```

---

## python-frontmatter Usage

### Install

```bash
uv add python-frontmatter
```

### Read a note

```python
import frontmatter

post = frontmatter.load("note.md")
print(post.metadata)     # dict of frontmatter properties
print(post.content)      # body text (without the --- delimiters)
```

### Create a new note with frontmatter

```python
post = frontmatter.Post("Note body here.", tags=["ai"], status="draft")
raw = frontmatter.dumps(post)
# Writes:
# ---
# tags:
# - ai
# status: draft
# ---
# Note body here.
```

### Merge properties into existing note

```python
post = frontmatter.load("note.md")
post.metadata.update({"status": "done", "reviewed": True})
with open("note.md", "w") as f:
    f.write(frontmatter.dumps(post))
```

### Remove a property

```python
post = frontmatter.load("note.md")
post.metadata.pop("draft", None)
with open("note.md", "w") as f:
    f.write(frontmatter.dumps(post))
```

### Parse from string

```python
post = frontmatter.loads("---\ntags: [ai]\n---\nBody here.")
```

---

## Notes

- `frontmatter.dumps()` always outputs the YAML block even if `metadata` is empty — results in `---\n---\nbody`.
  To omit frontmatter for notes with no properties, check `if post.metadata` before dumping.
- Property names are case-sensitive in Obsidian (use lowercase by convention).
- `tags` in YAML frontmatter and inline `#tags` are merged in Obsidian's tag index.
