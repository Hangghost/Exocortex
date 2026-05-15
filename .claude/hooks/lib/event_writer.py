"""
Shared lib for CC hook scripts.

Writes events to inbox/captured/cc_events/<session_id>/<event_type>_<ts>_<uuid>.json.
Hook layer is stateless write-only — no reads, no LLM, no network. Failures
fall back to ~/.claude/logs/hooks_failed/<date>.log and never block user input.

See openspec/specs/cc-hooks-capture/spec.md for the contract.
"""
import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Repo root: this file lives at <repo>/.claude/hooks/lib/event_writer.py.
# When .claude/hooks/ is git-tracked, every worktree gets its own copy of this
# file — naive parents[3] would resolve to the worktree root and split events
# across multiple inboxes. _resolve_main_repo_root() walks up to .git: if it's
# a directory, that's the main repo; if it's a file (worktree marker), parse
# `gitdir:` to recover the main repo root. Fallback to legacy parents[3] on
# any failure to honor the never-block-user-input contract.
def _resolve_main_repo_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        git_path = current / ".git"
        if git_path.is_dir():
            return current
        if git_path.is_file():
            content = git_path.read_text(encoding="utf-8").strip()
            for line in content.splitlines():
                if line.startswith("gitdir:"):
                    gitdir = Path(line.split(":", 1)[1].strip()).resolve()
                    return gitdir.parents[2]
            raise ValueError(f"Malformed .git file at {git_path}")
        if current.parent == current:
            raise ValueError(f"No git repo found above {start}")
        current = current.parent


try:
    REPO_ROOT = _resolve_main_repo_root(Path(__file__).parent)
except (ValueError, OSError):
    REPO_ROOT = Path(__file__).resolve().parents[3]
CC_EVENTS_DIR = REPO_ROOT / "inbox" / "captured" / "cc_events"
FALLBACK_LOG_DIR = Path.home() / ".claude" / "logs" / "hooks_failed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _compact_ts() -> str:
    """ISO8601-ish compact timestamp safe for filenames: 20260509T143022."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")


def _short_uuid() -> str:
    return uuid.uuid4().hex[:8]


def _safe_session_id(session_id: str | None) -> str:
    """Sanitize session_id for use as a directory name. Fallback to 'unknown'."""
    if not session_id:
        return "unknown"
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_")
    return safe[:64] or "unknown"


def write_event(
    event_type: str,
    session_id: str | None,
    payload: dict[str, Any],
    *,
    fixed_filename: str | None = None,
) -> Path | None:
    """
    Write a hook event to inbox/captured/cc_events/<session_id>/.

    Args:
        event_type: One of 'prompt' | 'session_done' | 'tool_error' | 'arch_change'.
        session_id: CC session UUID. None falls back to 'unknown'.
        payload: Event-specific fields. Will be merged with base envelope.
        fixed_filename: Override generated filename (used by SessionEnd which writes
                        a single _session_done.json per session).

    Returns:
        Path to the written file, or None on failure (errors go to fallback log).

    Never raises — failures must not block user input.
    """
    try:
        sid = _safe_session_id(session_id)
        session_dir = CC_EVENTS_DIR / sid
        session_dir.mkdir(parents=True, exist_ok=True)

        envelope = {
            "event_type": event_type,
            "captured_at": _now_iso(),
            **payload,
        }

        if fixed_filename:
            filename = fixed_filename
        else:
            filename = f"{event_type}_{_compact_ts()}_{_short_uuid()}.json"

        target = session_dir / filename
        target.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
    except Exception:
        _log_failure(event_type, session_id, traceback.format_exc())
        return None


def write_session_header(
    session_id: str | None,
    header_payload: dict[str, Any],
) -> Path | None:
    """
    Write a single session header file at
    inbox/captured/cc_events/<session_id>/session.json.

    Unlike `write_event()`, this is overwrite-style (single fixed filename
    `session.json`, no ts/uuid). Resume / clear / compact triggers SessionStart
    again and the new header replaces the old one — single-file semantics, the
    `source` field carries the trigger type.

    Args:
        session_id: CC session UUID. None falls back to 'unknown'.
        header_payload: Session-level fields. Spec defines six required:
            session_id, cwd, transcript_path, source, model, started_at.

    Returns:
        Path to session.json on success, or None on failure (errors go to
        fallback log via the same mechanism as write_event).
    """
    try:
        sid = _safe_session_id(session_id)
        session_dir = CC_EVENTS_DIR / sid
        session_dir.mkdir(parents=True, exist_ok=True)

        target = session_dir / "session.json"
        target.write_text(
            json.dumps(header_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
    except Exception:
        _log_failure("session_header", session_id, traceback.format_exc())
        return None


def _log_failure(event_type: str, session_id: str | None, tb: str) -> None:
    """Best-effort fallback log. Swallow errors here too — never raise to caller."""
    try:
        FALLBACK_LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = FALLBACK_LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                f"[{_now_iso()}] event_type={event_type} session={session_id}\n{tb}\n---\n"
            )
    except Exception:
        pass  # Truly nothing we can do; let CC continue


def read_payload_from_stdin() -> dict[str, Any]:
    """
    Read hook payload JSON from stdin.

    CC sends a JSON object on stdin to each hook script. This is the standard
    entry point for all hook scripts in this lib.
    Returns {} on parse failure (caller decides how to handle).
    """
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except Exception:
        _log_failure("stdin_parse", None, traceback.format_exc())
        return {}
