"""
cc_events_bridge — read CC hook events from inbox/captured/cc_events/, convert
to raw_signals JSON schema, write .processed marker.

Hook layer is stateless write-only; this bridge is the batch consumer that
promotes events into the standard raw_signals format for downstream stage1/2.

See:
  openspec/specs/cc-hooks-capture/spec.md
  openspec/specs/l0-signal-capture/spec.md (cc_event source)
  openspec/specs/v1-capture-pipeline/spec.md
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)

# Repo root: this file lives at <repo>/infra/periodic_jobs/ai_heartbeat/src/v1/capturer/cc_events_bridge.py
# parents[0]=capturer, [1]=v1, [2]=src, [3]=ai_heartbeat, [4]=periodic_jobs, [5]=infra, [6]=repo
REPO_ROOT = Path(__file__).resolve().parents[6]
CC_EVENTS_DIR = REPO_ROOT / "inbox" / "captured" / "cc_events"


def capture(target_date: str) -> list[dict[str, Any]]:
    """
    Public entry — match the calendar/email capturer signature so the dispatcher
    in capturer/main.py can register cc_events_bridge as a peer source.

    Returns a list of raw_signal dicts (each with id/source/captured_at/content/triage)
    for the dispatcher to write. Also writes `.processed` markers for events it
    successfully converts, so re-runs are idempotent.

    target_date is currently ignored — bridge processes all unprocessed events
    regardless of date (events from yesterday's session may still be in inbox).
    """
    signals: list[dict[str, Any]] = []
    processed_count = 0
    failed_count = 0
    skipped_count = 0

    if not CC_EVENTS_DIR.exists():
        logger.info("cc_events_bridge: no cc_events dir, skipping")
        return signals

    # Cache session headers once per session_dir to avoid re-reading session.json
    # for every event in the same session.
    header_cache: dict[Path, dict[str, Any] | None] = {}

    for event_path in _enumerate_unprocessed_events():
        try:
            event = _load_event(event_path)
        except Exception as e:
            logger.warning("cc_events_bridge: failed to parse %s: %s", event_path, e)
            failed_count += 1
            continue

        session_dir = event_path.parent
        if session_dir not in header_cache:
            header_cache[session_dir] = load_session_header(session_dir)

        try:
            signal = _to_raw_signal(event, event_path, header_cache[session_dir])
        except Exception as e:
            logger.warning("cc_events_bridge: failed to convert %s: %s", event_path, e)
            failed_count += 1
            continue

        if signal is None:
            skipped_count += 1
            continue

        signals.append(signal)
        try:
            _mark_processed(event_path)
            processed_count += 1
        except Exception as e:
            # If we can't write marker, the next run will re-emit — undesirable
            # but not catastrophic (downstream uses id-based upsert).
            logger.warning("cc_events_bridge: failed to mark processed %s: %s", event_path, e)

    logger.info(
        "cc_events_bridge: processed=%d skipped=%d failed=%d → %d signals",
        processed_count, skipped_count, failed_count, len(signals),
    )
    return signals


def load_session_header(session_dir: Path) -> dict[str, Any] | None:
    """
    Read session.json header from a session directory. Returns None if missing
    or malformed — bridge falls back to empty session-level fields rather than
    dropping events. session.json itself is not enumerated as an event.
    """
    header_path = session_dir / "session.json"
    if not header_path.exists():
        return None
    try:
        return json.loads(header_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("cc_events_bridge: malformed session.json at %s: %s", header_path, e)
        return None


def _enumerate_unprocessed_events() -> Iterator[Path]:
    """Yield event JSON files that have no sibling .processed marker.

    Skips `session.json` — that is the session header, consumed via
    `load_session_header()` rather than as an event.
    """
    for session_dir in sorted(CC_EVENTS_DIR.iterdir()):
        if not session_dir.is_dir():
            continue
        for event_path in sorted(session_dir.glob("*.json")):
            if event_path.name == "session.json":
                continue
            marker = event_path.with_suffix(event_path.suffix + ".processed")
            if marker.exists():
                continue
            yield event_path


def _load_event(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_raw_signal(
    event: dict[str, Any],
    event_path: Path,
    header: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Convert a hook event dict into the raw_signals JSON schema.

    Session-level fields (session_id, cwd, transcript_path, source, model) are
    folded in from the session header rather than the event body. When header
    is missing (hook fail or pre-SessionStart events), header-derived fields
    fall back to empty strings; the event still produces a signal.

    Returns None if the event is malformed or of an unknown type (caller treats
    as 'skipped' rather than 'failed').
    """
    event_type = event.get("event_type")
    captured_at = event.get("captured_at") or _now_iso()

    if not event_type:
        return None

    content = _build_content(event_type, event)
    if content is None:
        return None  # unknown event_type

    # session_id: prefer header, fall back to parent dir name (event_path is
    # under <session_id>/), fall back to "unknown".
    header = header or {}
    session_id = header.get("session_id") or event_path.parent.name or "unknown"

    # Stable id: short session prefix (8 chars) + filename stem.
    # Full UUID would push id past 64 chars and break Anthropic Batch API's
    # custom_id limit. 8-char session prefix + filename's own ts+uuid keeps
    # global uniqueness while staying under 64 chars.
    short_session = session_id[:8] if session_id and session_id != "unknown" else "unknown"
    signal_id = f"{short_session}_{event_path.stem}"

    return {
        "id": signal_id,
        "source": "cc_event",
        "captured_at": captured_at,
        "content": content,
        "triage": None,
        "event_type": event_type,
        "session_id": session_id,
        "cwd": header.get("cwd", ""),
        "transcript_path": header.get("transcript_path", ""),
        "session_source": header.get("source", ""),
        "model": header.get("model", ""),
        "origin_event_path": str(event_path.relative_to(REPO_ROOT)),
    }


def _build_content(event_type: str, event: dict[str, Any]) -> str | None:
    """Render event payload into a content string for downstream triage.

    Returns None for event types that are intentionally not consumed by
    triage (the caller treats them as 'skipped' and does NOT write a
    `.processed` marker, so they age out via the 30-day GC on the
    gitignored inbox buffer):

    - `arch_change`: hook removed in tune-cc-hooks-capture; legacy events
      may still exist in inbox.
    - `session_done` / `subagent_start`: metadata-only events filtered in
      prune-l0-capture-pipeline. content would be a status tag (e.g.
      `[session_done] reason=clear`) with no triage value; sending them to
      Haiku wastes Batch capacity and risks false-positive observer noise.
      Hooks still write the inbox files for potential windowing /
      diagnostic uses.
    """
    if event_type == "prompt":
        return event.get("prompt_text", "")
    if event_type == "tool_error":
        cmd = event.get("command", "")
        exit_code = event.get("exit_code", "?")
        stderr = event.get("stderr_excerpt", "")
        return f"[Bash exit={exit_code}] {cmd}\n{stderr}".strip()
    if event_type == "subagent_done":
        agent_id = event.get("agent_id", "?")
        agent_type = event.get("agent_type", "?")
        msg = event.get("last_assistant_message", "")
        return f"[subagent_done] {agent_type} agent_id={agent_id}\n{msg}".strip()
    return None


def _mark_processed(event_path: Path) -> None:
    """Write an empty `.processed` marker next to the event file."""
    marker = event_path.with_suffix(event_path.suffix + ".processed")
    marker.touch()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> None:
    """CLI entry — useful for manual triggers and testing."""
    import argparse
    parser = argparse.ArgumentParser(description="cc_events_bridge: convert hook events to raw_signals")
    parser.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    signals = capture(args.date)
    print(f"Produced {len(signals)} signals; markers written for processed events.")


if __name__ == "__main__":
    main()
