#!/usr/bin/env python3
"""
SubagentStart hook — capture subagent invocation.

Hook payload (verified empirically via probe in tune-cc-hooks-capture task 3.2):
  - session_id, transcript_path, cwd
  - agent_id (the subagent's runtime id, e.g. "afc74488c386d42ff")
  - agent_type (e.g. "general-purpose", "Explore", "Plan", ...)
  - hook_event_name: "SubagentStart"

Note: `description` is not in this payload; it lives on PreToolUse(Task)'s
tool_input.description. This capability captures lifecycle only.

Always exits 0. Failures go to ~/.claude/logs/hooks_failed/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_event  # noqa: E402


def main() -> int:
    payload = read_payload_from_stdin()
    write_event(
        "subagent_start",
        payload.get("session_id"),
        {
            "agent_id": payload.get("agent_id", ""),
            "agent_type": payload.get("agent_type", ""),
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
