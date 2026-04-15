#!/usr/bin/env python3
"""
organizer.py — AI-driven reorganization workflow for an Obsidian vault folder.

Usage:
    organizer.py analyze <folder>
    organizer.py execute [--moves JSON] [--frontmatter-updates JSON]
                         [--create-index FOLDER --title TEXT]
                         [--dry-run]

All commands output JSON to stdout. Errors go to stderr; exit code 1 on failure.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from client import ObsidianClient


# ------------------------------------------------------------------
# analyze
# ------------------------------------------------------------------

def cmd_analyze(client: ObsidianClient, args: argparse.Namespace) -> None:
    files = client.list(args.folder, recursive=True)
    if not files:
        print(f"[organizer] No .md files found in '{args.folder}'.", file=sys.stderr)
        print(json.dumps([]))
        return

    summary = []
    for rel_path in files:
        try:
            note = client.read(rel_path)
        except SystemExit:
            continue
        fm = note.get("frontmatter", {})
        body = note.get("body", "")
        words = len(body.split())
        title = fm.get("title") or Path(rel_path).stem
        tags = fm.get("tags", [])
        excerpt = body[:200].replace("\n", " ").strip()
        summary.append({
            "path": rel_path,
            "title": title,
            "tags": tags,
            "excerpt": excerpt,
            "word_count": words,
        })

    print(json.dumps(summary, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------
# execute
# ------------------------------------------------------------------

def cmd_execute(client: ObsidianClient, args: argparse.Namespace) -> None:
    dry_run = args.dry_run

    moves = []
    if args.moves:
        try:
            moves = json.loads(args.moves)
        except json.JSONDecodeError as e:
            print(f"[organizer] Error: invalid --moves JSON: {e}", file=sys.stderr)
            sys.exit(1)

    fm_updates = []
    if args.frontmatter_updates:
        try:
            fm_updates = json.loads(args.frontmatter_updates)
        except json.JSONDecodeError as e:
            print(f"[organizer] Error: invalid --frontmatter-updates JSON: {e}", file=sys.stderr)
            sys.exit(1)

    create_index_folder = args.create_index or ""
    index_title = args.title or ""

    # Validate: if creating index, title is required
    if create_index_folder and not index_title:
        print("[organizer] Error: --title is required with --create-index.", file=sys.stderr)
        sys.exit(1)

    results = {"moves": [], "frontmatter_updates": [], "index_notes": [], "failures": []}

    # --- Move operations ---
    for op in moves:
        src = op.get("src", "")
        dst = op.get("dst", "")
        if not src or not dst:
            results["failures"].append({"op": "move", "src": src, "dst": dst, "error": "src/dst required"})
            continue
        if dry_run:
            print(f"[dry-run] MOVE {src} → {dst}")
            results["moves"].append({"src": src, "dst": dst, "status": "dry-run"})
        else:
            try:
                client.move(src, dst)
                results["moves"].append({"src": src, "dst": dst, "status": "ok"})
            except SystemExit:
                results["failures"].append({"op": "move", "src": src, "dst": dst, "error": "move failed"})
            except Exception as e:
                results["failures"].append({"op": "move", "src": src, "dst": dst, "error": str(e)})

    # --- Frontmatter updates ---
    for op in fm_updates:
        path = op.get("path", "")
        set_data = op.get("set", {})
        remove_key = op.get("remove", "")
        if not path:
            results["failures"].append({"op": "frontmatter", "path": path, "error": "path required"})
            continue
        if dry_run:
            print(f"[dry-run] FRONTMATTER {path} set={json.dumps(set_data)} remove={remove_key}")
            results["frontmatter_updates"].append({"path": path, "status": "dry-run"})
        else:
            try:
                client.frontmatter_update(path, set_data=set_data or None, remove_key=remove_key or None)
                results["frontmatter_updates"].append({"path": path, "status": "ok"})
            except SystemExit:
                results["failures"].append({"op": "frontmatter", "path": path, "error": "update failed"})
            except Exception as e:
                results["failures"].append({"op": "frontmatter", "path": path, "error": str(e)})

    # --- Create index (MOC) ---
    if create_index_folder:
        files = client.list(create_index_folder, recursive=False)
        index_path = f"{create_index_folder.rstrip('/')}/index.md"
        lines = [f"# {index_title}", ""]
        for f in sorted(files):
            stem = Path(f).stem
            rel = Path(f).name
            if rel == "index.md":
                continue
            lines.append(f"- [[{stem}]]")
        content = "\n".join(lines) + "\n"
        if dry_run:
            print(f"[dry-run] CREATE INDEX {index_path}")
            print(content)
            results["index_notes"].append({"path": index_path, "status": "dry-run"})
        else:
            try:
                client.write(index_path, content=content)
                results["index_notes"].append({"path": index_path, "status": "ok"})
            except Exception as e:
                results["failures"].append({"op": "create-index", "path": index_path, "error": str(e)})

    # --- Summary ---
    n_moves = sum(1 for r in results["moves"] if r["status"] in ("ok", "dry-run"))
    n_fm = sum(1 for r in results["frontmatter_updates"] if r["status"] in ("ok", "dry-run"))
    n_idx = sum(1 for r in results["index_notes"] if r["status"] in ("ok", "dry-run"))
    n_fail = len(results["failures"])

    label = "[dry-run] " if dry_run else ""
    print(f"[organizer] {label}{n_moves} files moved, {n_fm} frontmatter updates, {n_idx} index notes created.", file=sys.stderr)
    if n_fail:
        print(f"[organizer] {n_fail} failure(s):", file=sys.stderr)
        for f in results["failures"]:
            print(f"  - {f}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))

    if n_fail:
        sys.exit(1)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI-driven Obsidian vault organizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    # analyze
    a = sub.add_parser("analyze", help="Summarize all notes in a folder for AI analysis")
    a.add_argument("folder", help="Folder relative to vault root")

    # execute
    e = sub.add_parser("execute", help="Execute reorganization operations")
    e.add_argument("--moves", default="", help='JSON array: [{"src": "...", "dst": "..."}]')
    e.add_argument("--frontmatter-updates", default="", help='JSON array: [{"path": "...", "set": {...}, "remove": "key"}]')
    e.add_argument("--create-index", default="", metavar="FOLDER", help="Generate index.md (MOC) in FOLDER")
    e.add_argument("--title", default="", help="Title for the generated index note")
    e.add_argument("--dry-run", action="store_true", help="Print planned operations without executing")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config()
    client = ObsidianClient(config)

    if args.command == "analyze":
        cmd_analyze(client, args)
    elif args.command == "execute":
        cmd_execute(client, args)


if __name__ == "__main__":
    main()
