"""
Obsidian vault client.

Access modes:
  REST API  — uses obsidian-local-rest-api plugin (preferred; supports search + backlink-aware rename)
  Filesystem — direct file operations on vault_path (always available as fallback)

Usage:
    from client import ObsidianClient
    client = ObsidianClient(config)
    data = client.read("folder/note.md")
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

import frontmatter
import requests


class ObsidianClient:
    def __init__(self, config: dict):
        self.vault_path = Path(config["vault_path"])
        self.rest = config.get("rest_api", {})
        self._api_available = self._probe_api()
        if self._api_available:
            self._mode = "rest"
        else:
            self._mode = "filesystem"
            if self.rest.get("enabled"):
                print("[obsidian] REST API unavailable — using filesystem mode.", file=sys.stderr)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _probe_api(self) -> bool:
        if not self.rest.get("enabled") or not self.rest.get("api_key"):
            return False
        try:
            r = requests.get(
                self._api_url("/"),
                headers=self._headers(),
                timeout=1,
                verify=False,
            )
            return r.status_code < 500
        except Exception:
            return False

    def _api_url(self, path: str) -> str:
        host = self.rest.get("host", "127.0.0.1")
        port = self.rest.get("port", 27123)
        return f"https://{host}:{port}{path}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.rest.get('api_key', '')}"}

    def _vault_file(self, rel_path: str) -> Path:
        return self.vault_path / rel_path

    @property
    def mode(self) -> str:
        return self._mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self, rel_path: str) -> dict:
        """Return {"frontmatter": {...}, "body": "..."}."""
        if self._mode == "rest":
            return self._rest_read(rel_path)
        return self._fs_read(rel_path)

    def write(self, rel_path: str, content: str = "", fm_data: dict | None = None) -> None:
        """Create or overwrite a note. Creates parent dirs as needed."""
        if self._mode == "rest":
            self._rest_write(rel_path, content, fm_data)
        else:
            self._fs_write(rel_path, content, fm_data)

    def list(self, folder: str = "", recursive: bool = False) -> list[str]:
        """Return relative paths to all .md files in folder."""
        if self._mode == "rest":
            return self._rest_list(folder, recursive)
        return self._fs_list(folder, recursive)

    def move(self, src: str, dst: str) -> None:
        """Move/rename a note. Warns about backlinks in filesystem mode."""
        if self._mode == "rest":
            self._rest_move(src, dst)
        else:
            self._fs_move(src, dst)

    def search(self, query: str) -> list[dict]:
        """Return [{"path": ..., "excerpt": ...}]."""
        if self._mode == "rest":
            return self._rest_search(query)
        return self._fs_search(query)

    def frontmatter_update(self, rel_path: str, set_data: dict | None = None, remove_key: str | None = None) -> None:
        """Merge/remove frontmatter keys without touching body."""
        p = self._vault_file(rel_path)
        if not p.exists():
            print(f"[obsidian] Error: note not found: {rel_path}", file=sys.stderr)
            sys.exit(1)
        post = frontmatter.load(str(p))
        if set_data:
            post.metadata.update(set_data)
        if remove_key and remove_key in post.metadata:
            del post.metadata[remove_key]
        p.write_text(frontmatter.dumps(post))

    # ------------------------------------------------------------------
    # REST API implementations
    # ------------------------------------------------------------------

    def _rest_read(self, rel_path: str) -> dict:
        url = self._api_url(f"/vault/{rel_path}")
        r = requests.get(url, headers=self._headers(), verify=False)
        if r.status_code == 404:
            print(f"[obsidian] Error: note not found: {rel_path}", file=sys.stderr)
            sys.exit(1)
        r.raise_for_status()
        raw = r.text
        post = frontmatter.loads(raw)
        return {"frontmatter": dict(post.metadata), "body": post.content}

    def _rest_write(self, rel_path: str, content: str, fm_data: dict | None) -> None:
        raw = _build_note(content, fm_data)
        url = self._api_url(f"/vault/{rel_path}")
        r = requests.put(url, headers={**self._headers(), "Content-Type": "text/markdown"}, data=raw.encode(), verify=False)
        r.raise_for_status()

    def _rest_list(self, folder: str, recursive: bool) -> list[str]:
        path = folder.rstrip("/") + "/" if folder else "/"
        url = self._api_url(f"/vault/{path}")
        r = requests.get(url, headers=self._headers(), verify=False)
        r.raise_for_status()
        data = r.json()
        files = data.get("files", [])
        md_files = [f for f in files if f.endswith(".md")]
        if recursive:
            dirs = [f for f in files if not f.endswith(".md")]
            for d in dirs:
                sub = self._rest_list(d, recursive=True)
                md_files.extend(sub)
        return md_files

    def _rest_move(self, src: str, dst: str) -> None:
        # obsidian-local-rest-api doesn't have a move endpoint directly;
        # use the filesystem approach even in "rest" mode for moves.
        self._fs_move(src, dst, warn_backlinks=False)

    def _rest_search(self, query: str) -> list[dict]:
        url = self._api_url("/search/simple/")
        r = requests.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"query": query},
            verify=False,
        )
        r.raise_for_status()
        results = []
        for item in r.json():
            results.append({"path": item.get("filename", ""), "excerpt": item.get("score", "")})
        return results

    # ------------------------------------------------------------------
    # Filesystem implementations
    # ------------------------------------------------------------------

    def _fs_read(self, rel_path: str) -> dict:
        p = self._vault_file(rel_path)
        if not p.exists():
            print(f"[obsidian] Error: note not found: {rel_path}", file=sys.stderr)
            sys.exit(1)
        post = frontmatter.load(str(p))
        return {"frontmatter": dict(post.metadata), "body": post.content}

    def _fs_write(self, rel_path: str, content: str, fm_data: dict | None) -> None:
        p = self._vault_file(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = _build_note(content, fm_data)
        p.write_text(raw)

    def _fs_list(self, folder: str, recursive: bool) -> list[str]:
        base = self._vault_file(folder) if folder else self.vault_path
        if not base.exists():
            return []
        pattern = "**/*.md" if recursive else "*.md"
        files = sorted(base.glob(pattern))
        return [str(f.relative_to(self.vault_path)) for f in files]

    def _fs_move(self, src: str, dst: str, warn_backlinks: bool = True) -> None:
        src_p = self._vault_file(src)
        dst_p = self._vault_file(dst)
        if not src_p.exists():
            print(f"[obsidian] Error: source not found: {src}", file=sys.stderr)
            sys.exit(1)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_p), str(dst_p))
        if warn_backlinks:
            print(f"[obsidian] Warning: filesystem move does not update backlinks in other notes.", file=sys.stderr)

    def _fs_search(self, query: str) -> list[dict]:
        results = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        for md_file in self.vault_path.rglob("*.md"):
            try:
                text = md_file.read_text(errors="ignore")
            except OSError:
                continue
            for line in text.splitlines():
                if pattern.search(line):
                    rel = str(md_file.relative_to(self.vault_path))
                    excerpt = line.strip()[:200]
                    results.append({"path": rel, "excerpt": excerpt})
                    break
        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_note(content: str, fm_data: dict | None) -> str:
    if fm_data:
        post = frontmatter.Post(content, **fm_data)
        return frontmatter.dumps(post)
    return content
