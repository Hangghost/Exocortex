#!/usr/bin/env python3
"""
obsidian.py — Atomic CLI operations on an Obsidian vault.

Usage:
    obsidian.py read <path>
    obsidian.py write <path> [--content TEXT] [--frontmatter JSON]
    obsidian.py list <folder> [--recursive]
    obsidian.py move <src> <dst>
    obsidian.py frontmatter <path> [--set JSON] [--remove KEY]
    obsidian.py search <query>

All commands output JSON to stdout. Errors go to stderr; exit code 1 on failure.
"""

import argparse
import json
import sys
from pathlib import Path

# Make scripts/ importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from client import ObsidianClient


def cmd_read(client: ObsidianClient, args: argparse.Namespace) -> None:
    result = client.read(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_write(client: ObsidianClient, args: argparse.Namespace) -> None:
    content = args.content or ""
    fm_data = None
    if args.frontmatter:
        try:
            fm_data = json.loads(args.frontmatter)
        except json.JSONDecodeError as e:
            print(f"[obsidian] Error: invalid --frontmatter JSON: {e}", file=sys.stderr)
            sys.exit(1)
    client.write(args.path, content, fm_data)
    print(json.dumps({"status": "ok", "path": args.path}))


def cmd_list(client: ObsidianClient, args: argparse.Namespace) -> None:
    files = client.list(args.folder, recursive=args.recursive)
    print(json.dumps(files, ensure_ascii=False))


def cmd_move(client: ObsidianClient, args: argparse.Namespace) -> None:
    client.move(args.src, args.dst)
    print(json.dumps({"status": "ok", "src": args.src, "dst": args.dst}))


def cmd_frontmatter(client: ObsidianClient, args: argparse.Namespace) -> None:
    set_data = None
    if args.set:
        try:
            set_data = json.loads(args.set)
        except json.JSONDecodeError as e:
            print(f"[obsidian] Error: invalid --set JSON: {e}", file=sys.stderr)
            sys.exit(1)
    client.frontmatter_update(args.path, set_data=set_data, remove_key=args.remove)
    print(json.dumps({"status": "ok", "path": args.path}))


def cmd_search(client: ObsidianClient, args: argparse.Namespace) -> None:
    results = client.search(args.query)
    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Atomic Obsidian vault operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # read
    r = sub.add_parser("read", help="Read a note (returns frontmatter + body JSON)")
    r.add_argument("path", help="Path relative to vault root (e.g. folder/note.md)")

    # write
    w = sub.add_parser("write", help="Create or overwrite a note")
    w.add_argument("path", help="Path relative to vault root")
    w.add_argument("--content", default="", help="Note body text")
    w.add_argument("--frontmatter", default="", help='YAML frontmatter as JSON (e.g. \'{"tags":["ai"]}\')')

    # list
    ls = sub.add_parser("list", help="List .md files in a folder")
    ls.add_argument("folder", nargs="?", default="", help="Folder relative to vault root (empty = root)")
    ls.add_argument("--recursive", action="store_true", help="Include subfolders")

    # move
    mv = sub.add_parser("move", help="Move or rename a note")
    mv.add_argument("src", help="Source path relative to vault root")
    mv.add_argument("dst", help="Destination path relative to vault root")

    # frontmatter
    fm = sub.add_parser("frontmatter", help="Update frontmatter properties")
    fm.add_argument("path", help="Path relative to vault root")
    fm.add_argument("--set", default="", help='Frontmatter properties to merge as JSON (e.g. \'{"tags":["ai"]}\')')
    fm.add_argument("--remove", default="", help="Frontmatter key to remove")

    # search
    s = sub.add_parser("search", help="Search notes by keyword")
    s.add_argument("query", help="Search query string")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config()
    client = ObsidianClient(config)

    dispatch = {
        "read": cmd_read,
        "write": cmd_write,
        "list": cmd_list,
        "move": cmd_move,
        "frontmatter": cmd_frontmatter,
        "search": cmd_search,
    }
    dispatch[args.command](client, args)


if __name__ == "__main__":
    main()
