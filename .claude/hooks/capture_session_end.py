#!/usr/bin/env python3
"""
SessionEnd hook — write a single _session_done.json marker per session.

Hook payload typically includes:
  - session_id, transcript_path, cwd, reason
We don't compute prompt_count or duration here — that's bridge's job by reading
the transcript jsonl. Hook layer is stateless write-only.

Always exits 0. Single fixed filename means a re-fire (rare) overwrites — single-file semantics.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_event  # noqa: E402


def main() -> int:
    payload = read_payload_from_stdin()
    write_event(
        "session_done",
        payload.get("session_id"),
        {"reason": payload.get("reason", "unknown")},
        fixed_filename="_session_done.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
