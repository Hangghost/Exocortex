#!/usr/bin/env python3
"""
PostToolUseFailure hook — capture Bash failures.

Registered against PostToolUseFailure (not PostToolUse) per CC docs:
PostToolUse fires only on success; failures route through the dedicated
PostToolUseFailure event. So if this hook fires at all, the tool failed.

Hook payload (verified empirically + docs):
  - session_id, transcript_path, cwd
  - tool_name (filtered to "Bash" via matcher)
  - tool_input: {command, description?, ...}
  - tool_response: {stdout, stderr, interrupted, isImage,
                    returnCodeInterpretation?, noOutputExpected, ...}
    Note: there is no numeric exit_code field; CC summarizes via
    returnCodeInterpretation when available.

Defensive: capture whatever fields are present, truncate large strings.
Always exits 0 — never block CC.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_event  # noqa: E402


MAX_CHARS = 2000


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return str(text)[:limit]


def main() -> int:
    payload = read_payload_from_stdin()

    # Matcher already filtered to Bash, but double-check defensively.
    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}

    write_event(
        "tool_error",
        payload.get("session_id"),
        {
            "tool_name": "Bash",
            "command": tool_input.get("command", ""),
            "description": tool_input.get("description", ""),
            "stderr_excerpt": _truncate(tool_response.get("stderr"), MAX_CHARS),
            "stdout_excerpt": _truncate(tool_response.get("stdout"), MAX_CHARS),
            "interpretation": _truncate(tool_response.get("returnCodeInterpretation"), MAX_CHARS),
            "interrupted": bool(tool_response.get("interrupted", False)),
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
