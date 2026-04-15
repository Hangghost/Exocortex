# Obsidian Local REST API — Endpoint Reference

Plugin: [obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)

Base URL: `https://127.0.0.1:27123` (HTTPS only; self-signed cert — use `verify=False`)

All requests require the header:
```
Authorization: Bearer <api_key>
```

---

## Endpoints Used by This Skill

### GET /

Health check / probe. Used to detect if REST API is available.

**Response 200**:
```json
{"status": "OK", "versions": {...}}
```

**Usage**: If this times out (>1s) or errors, fall back to filesystem mode.

---

### GET /vault/{path}

Read a file or list a directory.

- If `path` ends with `/` → returns directory listing
- If `path` is a file → returns raw file content as text/markdown

**List directory response**:
```json
{
  "files": ["note1.md", "note2.md", "subfolder/"]
}
```

**Read file response**: raw Markdown text (includes frontmatter if present)

**404**: File or folder not found.

---

### PUT /vault/{path}

Create or overwrite a file.

**Request body**: raw Markdown text (Content-Type: text/markdown)

**Response 200/204**: Success (no body or `{"message": "ok"}`)

Creates parent directories automatically.

---

### POST /search/simple/

Full-text search across the vault.

**Request body**:
```json
{"query": "search terms here"}
```

**Response**:
```json
[
  {
    "filename": "folder/note.md",
    "score": 1.23,
    "matches": [{"context": "...surrounding text..."}]
  }
]
```

---

### POST /commands/execute

Execute an Obsidian command by ID (e.g., rename with backlink update).

**Request body**:
```json
{"commandId": "editor:rename-file"}
```

> Note: This skill does not currently use this endpoint. File moves are done
> via filesystem operations. Future enhancement could use this for backlink-aware rename.

---

## Notes

- The plugin uses a **self-signed TLS certificate** — always pass `verify=False` to requests.
- Default port is **27123**; configurable in plugin settings.
- The API key is shown in Obsidian → Settings → Local REST API.
- The API is only available when Obsidian is running with the plugin enabled.
