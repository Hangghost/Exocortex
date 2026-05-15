#!/usr/bin/env python3
"""
SessionStart hook — write a single session.json header per session.

Hook payload (CC sends on stdin) typically includes:
  - session_id, transcript_path, cwd, source, model, hook_event_name

`source` is one of: startup | resume | clear | compact (per CC docs).
We add `started_at` locally to capture the actual hook fire time, since
CC payload doesn't always include it.

Single-file overwrite semantics: resume / clear / compact triggers
SessionStart again and replaces the previous header. Bridge reads the
latest header to join session-level fields into raw_signals.

Always exits 0 to never block the session. Failures go to
~/.claude/logs/hooks_failed/ via event_writer fallback.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_session_header  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    payload = read_payload_from_stdin()
    session_id = payload.get("session_id")

    header = {
        "session_id": session_id or "unknown",
        "cwd": payload.get("cwd", ""),
        "transcript_path": payload.get("transcript_path", ""),
        "source": payload.get("source", "unknown"),
        "model": payload.get("model", ""),
        "started_at": _now_iso(),
    }
    write_session_header(session_id, header)
    return 0


if __name__ == "__main__":
    sys.exit(main())
