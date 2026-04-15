#!/usr/bin/env python3
"""
rename_project.py — Rename a project in the Exocortex system.

Usage:
    python infra/tools/rename_project.py <old_name> <new_name>

What it does:
    1. mv projects/<old>/ → projects/<new>/
    2. Update projects/INDEX.md: replace name column entry
    3. Batch-replace frontmatter `project: <old>` in:
       - contexts/work_logs/
       - contexts/thought_review/
       - contexts/blog/

Idempotent: if projects/<new>/ already exists, script exits with error.
"""

import sys
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
CONTEXTS_DIRS = [
    REPO_ROOT / "contexts" / "work_logs",
    REPO_ROOT / "contexts" / "thought_review",
    REPO_ROOT / "contexts" / "blog",
]


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def replace_in_file(path: Path, old: str, new: str) -> bool:
    """Replace all occurrences of old with new in file. Returns True if changed."""
    content = path.read_text(encoding="utf-8")
    new_content = content.replace(old, new)
    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python infra/tools/rename_project.py <old_name> <new_name>")
        sys.exit(1)

    old_name = sys.argv[1]
    new_name = sys.argv[2]

    # Validate kebab-case
    kebab_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    if not kebab_pattern.match(old_name):
        die(f"<old_name> '{old_name}' is not kebab-case")
    if not kebab_pattern.match(new_name):
        die(f"<new_name> '{new_name}' is not kebab-case")

    old_dir = PROJECTS_DIR / old_name
    new_dir = PROJECTS_DIR / new_name

    # Pre-condition checks
    if not old_dir.exists():
        die(f"projects/{old_name}/ does not exist")
    if new_dir.exists():
        die(f"projects/{new_name}/ already exists — aborting to avoid overwrite")

    print(f"Renaming project: {old_name} → {new_name}")
    print()

    # Step 1: mv projects/<old> → projects/<new>
    old_dir.rename(new_dir)
    print(f"  [1/3] Moved projects/{old_name}/ → projects/{new_name}/")

    # Step 2: Update projects/INDEX.md
    index_path = PROJECTS_DIR / "INDEX.md"
    if index_path.exists():
        changed = replace_in_file(index_path, f"| {old_name} |", f"| {new_name} |")
        if changed:
            print(f"  [2/3] Updated projects/INDEX.md")
        else:
            print(f"  [2/3] projects/INDEX.md — no match for '{old_name}' (check manually)")
    else:
        print(f"  [2/3] projects/INDEX.md not found, skipping")

    # Step 3: Batch-replace frontmatter in contexts/
    old_frontmatter = f"project: {old_name}"
    new_frontmatter = f"project: {new_name}"
    total_changed = 0

    for ctx_dir in CONTEXTS_DIRS:
        if not ctx_dir.exists():
            continue
        for md_file in ctx_dir.rglob("*.md"):
            if replace_in_file(md_file, old_frontmatter, new_frontmatter):
                print(f"          Updated frontmatter in {md_file.relative_to(REPO_ROOT)}")
                total_changed += 1

    if total_changed > 0:
        print(f"  [3/3] Updated {total_changed} context file(s)")
    else:
        print(f"  [3/3] No context files with 'project: {old_name}' found")

    print()
    print(f"Done. Project renamed: {old_name} → {new_name}")
    print(f"Note: openspec/changes/ links to change names, not project names — no update needed there.")


if __name__ == "__main__":
    main()
