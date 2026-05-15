#!/usr/bin/env python3
"""
SubagentStop hook — capture subagent completion.

Hook payload (verified empirically via probe in tune-cc-hooks-capture task 3.2):
  - session_id, transcript_path, cwd
  - permission_mode
  - agent_id, agent_type
  - effort: {level}
  - hook_event_name: "SubagentStop"
  - stop_hook_active: bool
  - agent_transcript_path
  - last_assistant_message: subagent's final response text

Note: there is no explicit success/error status field; downstream stages can
infer from `last_assistant_message` presence and the agent's transcript.

Always exits 0. Failures go to ~/.claude/logs/hooks_failed/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_event  # noqa: E402


MAX_MESSAGE_CHARS = 4000


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return str(text)[:limit]


def main() -> int:
    payload = read_payload_from_stdin()
    write_event(
        "subagent_done",
        payload.get("session_id"),
        {
            "agent_id": payload.get("agent_id", ""),
            "agent_type": payload.get("agent_type", ""),
            "last_assistant_message": _truncate(
                payload.get("last_assistant_message"), MAX_MESSAGE_CHARS
            ),
            "agent_transcript_path": payload.get("agent_transcript_path", ""),
            "stop_hook_active": bool(payload.get("stop_hook_active", False)),
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
