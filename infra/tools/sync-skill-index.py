#!/usr/bin/env python3
"""Rebuild rules/skills/INDEX.md from SKILL.md frontmatter.

Usage:
    uv run --with pyyaml tools/sync-skill-index.py
"""

import pathlib
import yaml

REPO_ROOT = pathlib.Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "rules" / "skills"
INDEX_PATH = SKILLS_DIR / "INDEX.md"


def parse_frontmatter(path: pathlib.Path) -> dict:
    """Extract YAML frontmatter from a file delimited by '---'."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def collect_skills() -> list[dict]:
    skills = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        fm = parse_frontmatter(skill_md)
        name = fm.get("name", skill_md.parent.name)
        description = fm.get("description", "").strip()
        rel_path = skill_md.relative_to(REPO_ROOT)
        skills.append({"name": name, "description": description, "path": rel_path})
    return skills


def build_index(skills: list[dict]) -> str:
    header = """\
# Skills Index

系統 skills 的能力速查入口。Session 啟動時被動載入此索引（metadata only）；需要執行某項能力時，再讀取對應的完整 `SKILL.md`。

**系統 skills**（本索引，`rules/skills/`）與 **agent-specific skills**（如 `.claude/skills/`）互補，合併為本次 session 的完整能力圖。

---

## 系統 Skills

| Name | Description | 路徑 |
|------|-------------|------|
"""
    rows = ""
    for s in skills:
        desc = s["description"].replace("\n", " ")
        rows += f"| {s['name']} | {desc} | `{s['path']}` |\n"

    footer = """
---

*每新增或刪除一個 skill，請同步更新本表格。可執行 `tools/sync-skill-index.py` 自動重建。*
"""
    return header + rows + footer


def main():
    skills = collect_skills()
    content = build_index(skills)
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {INDEX_PATH} with {len(skills)} skill(s):")
    for s in skills:
        print(f"  - {s['name']}")


if __name__ == "__main__":
    main()
