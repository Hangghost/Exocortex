#!/usr/bin/env python3
"""
UserPromptSubmit hook — write each user prompt to inbox/captured/cc_events/.

Hook payload (CC sends on stdin) typically includes:
  - session_id, transcript_path, cwd, hook_event_name, prompt
Schema may evolve; we use defensive .get() for all fields.

System-injected prompts (task notifications, monitor events) are filtered out
by exact-marker match — these are NOT user input despite firing the hook.
This is an origin filter (mechanical string match), not a value-judgment
filter, so it does NOT violate Decision 2 (no value filtering in hook).

Always exits 0 to never block user input. Failures go to ~/.claude/logs/hooks_failed/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.event_writer import read_payload_from_stdin, write_event  # noqa: E402


# Origin filter: prompts that begin with these markers are CC-injected system
# events, not user input. Kept as a small explicit list so each addition is
# audited rather than relying on heuristics.
SYSTEM_INJECTION_MARKERS: tuple[str, ...] = (
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
    "<task-notification>",
)


def _is_system_injected(prompt_text: str) -> bool:
    if not prompt_text:
        return False
    head = prompt_text.lstrip()[:500]
    return any(marker in head for marker in SYSTEM_INJECTION_MARKERS)


def main() -> int:
    payload = read_payload_from_stdin()
    prompt_text = payload.get("prompt", "")

    if _is_system_injected(prompt_text):
        return 0

    write_event(
        "prompt",
        payload.get("session_id"),
        {"prompt_text": prompt_text},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
