"""
Unit tests for cc_events_bridge.

Run with:
    python -m unittest infra.periodic_jobs.ai_heartbeat.src.v1.capturer.test_cc_events_bridge

Or directly:
    python infra/periodic_jobs/ai_heartbeat/src/v1/capturer/test_cc_events_bridge.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))

from infra.periodic_jobs.ai_heartbeat.src.v1.capturer import cc_events_bridge as bridge  # noqa: E402


class CCEventsBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp.name)
        self.cc_dir = self.tmp_root / "cc_events"
        self.cc_dir.mkdir(parents=True)
        self._cc_patch = patch.object(bridge, "CC_EVENTS_DIR", self.cc_dir)
        self._root_patch = patch.object(bridge, "REPO_ROOT", self.tmp_root)
        self._cc_patch.start()
        self._root_patch.start()

    def tearDown(self) -> None:
        self._cc_patch.stop()
        self._root_patch.stop()
        self.tmp.cleanup()

    def _write_event(self, session_id: str, name: str, payload: dict) -> Path:
        sess_dir = self.cc_dir / session_id
        sess_dir.mkdir(exist_ok=True)
        path = sess_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _write_session_header(self, session_id: str, header: dict) -> Path:
        sess_dir = self.cc_dir / session_id
        sess_dir.mkdir(exist_ok=True)
        path = sess_dir / "session.json"
        path.write_text(json.dumps(header), encoding="utf-8")
        return path

    def test_no_events_returns_empty(self) -> None:
        signals = bridge.capture("2026-05-09")
        self.assertEqual(signals, [])

    def test_prompt_event_converts_to_signal(self) -> None:
        self._write_session_header("sess1", {
            "session_id": "sess1",
            "cwd": "/repo",
            "transcript_path": "/repo/t.jsonl",
            "source": "startup",
            "model": "claude-opus-4-7",
            "started_at": "2026-05-09T17:55:00+08:00",
        })
        self._write_event("sess1", "prompt_x_y.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "hello world",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(len(signals), 1)
        s = signals[0]
        self.assertEqual(s["source"], "cc_event")
        self.assertEqual(s["event_type"], "prompt")
        self.assertEqual(s["session_id"], "sess1")
        self.assertEqual(s["content"], "hello world")
        self.assertIsNone(s["triage"])
        self.assertIn("origin_event_path", s)
        # session-level fields folded in from header
        self.assertEqual(s["cwd"], "/repo")
        self.assertEqual(s["transcript_path"], "/repo/t.jsonl")
        self.assertEqual(s["session_source"], "startup")
        self.assertEqual(s["model"], "claude-opus-4-7")

    def test_event_without_session_header_falls_back(self) -> None:
        # No session.json — header_join should yield empty session-level fields
        # and use parent dir name as session_id; event still produces a signal.
        self._write_event("sess1", "prompt_x_y.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "no header here",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(len(signals), 1)
        s = signals[0]
        self.assertEqual(s["session_id"], "sess1")
        self.assertEqual(s["cwd"], "")
        self.assertEqual(s["transcript_path"], "")
        self.assertEqual(s["session_source"], "")
        self.assertEqual(s["model"], "")
        self.assertEqual(s["content"], "no header here")

    def test_session_json_not_treated_as_event(self) -> None:
        self._write_session_header("sess1", {
            "session_id": "sess1",
            "cwd": "/repo",
            "transcript_path": "/repo/t.jsonl",
            "source": "startup",
            "model": "claude-opus-4-7",
            "started_at": "2026-05-09T17:55:00+08:00",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(signals, [])
        # session.json must not get a .processed marker
        marker = (self.cc_dir / "sess1" / "session.json").with_suffix(".json.processed")
        self.assertFalse(marker.exists())

    def test_tool_error_content_includes_cmd_and_stderr(self) -> None:
        self._write_event("sess1", "tool_error_a_b.json", {
            "event_type": "tool_error",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "command": "false",
            "exit_code": 1,
            "stderr_excerpt": "boom",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(len(signals), 1)
        self.assertIn("false", signals[0]["content"])
        self.assertIn("boom", signals[0]["content"])
        self.assertIn("exit=1", signals[0]["content"])

    def test_arch_change_event_no_longer_processed(self) -> None:
        # arch_change hook was removed in tune-cc-hooks-capture; old events
        # still in inbox should be skipped (no signal, no marker, GC cleans).
        path = self._write_event("sess1", "arch_change_a_b.json", {
            "event_type": "arch_change",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "tool_name": "Edit",
            "file_path": "rules/SOUL.md",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(signals, [])
        marker = path.with_suffix(path.suffix + ".processed")
        self.assertFalse(marker.exists())

    def test_session_done_event_filtered(self) -> None:
        # session_done is metadata-only (content would be `[session_done] reason=X`);
        # bridge skips it so triage isn't polluted with windowing signals. Hooks
        # still write the inbox file for diagnostic uses; 30-day GC cleans up.
        path = self._write_event("sess1", "_session_done.json", {
            "event_type": "session_done",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "reason": "exit",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(signals, [])
        marker = path.with_suffix(path.suffix + ".processed")
        self.assertFalse(marker.exists())

    def test_subagent_start_event_filtered(self) -> None:
        # subagent_start is metadata-only (no content beyond agent type/id);
        # bridge skips it. subagent_done carries the assistant message and is
        # still consumed.
        path = self._write_event("sess1", "subagent_start_x_y.json", {
            "event_type": "subagent_start",
            "captured_at": "2026-05-10T08:30:00+08:00",
            "agent_id": "abc12345",
            "agent_type": "general-purpose",
        })
        signals = bridge.capture("2026-05-10")
        self.assertEqual(signals, [])
        marker = path.with_suffix(path.suffix + ".processed")
        self.assertFalse(marker.exists())

    def test_subagent_done_event_includes_message(self) -> None:
        self._write_event("sess1", "subagent_done_x_y.json", {
            "event_type": "subagent_done",
            "captured_at": "2026-05-10T08:31:00+08:00",
            "agent_id": "abc12345",
            "agent_type": "general-purpose",
            "last_assistant_message": "task done",
        })
        signals = bridge.capture("2026-05-10")
        self.assertEqual(len(signals), 1)
        s = signals[0]
        self.assertEqual(s["event_type"], "subagent_done")
        self.assertIn("task done", s["content"])

    def test_idempotency_skips_processed_events(self) -> None:
        self._write_event("sess1", "prompt_x_y.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "hi",
        })
        first = bridge.capture("2026-05-09")
        second = bridge.capture("2026-05-09")
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)  # all events have .processed marker now

    def test_processed_marker_written(self) -> None:
        path = self._write_event("sess1", "prompt_x_y.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "hi",
        })
        bridge.capture("2026-05-09")
        marker = path.with_suffix(path.suffix + ".processed")
        self.assertTrue(marker.exists())

    def test_malformed_json_does_not_block_others(self) -> None:
        # One bad file, one good file
        bad = self.cc_dir / "sess1" / "prompt_bad.json"
        bad.parent.mkdir(exist_ok=True)
        bad.write_text("{not json", encoding="utf-8")
        self._write_event("sess1", "prompt_good.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "ok",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["content"], "ok")
        # Bad file should NOT have a .processed marker (so a future fix-and-retry works)
        bad_marker = bad.with_suffix(bad.suffix + ".processed")
        self.assertFalse(bad_marker.exists())

    def test_unknown_event_type_skipped_no_marker(self) -> None:
        path = self._write_event("sess1", "weird_xyz.json", {
            "event_type": "no_such_type",
            "session_id": "sess1",
            "captured_at": "2026-05-09T18:00:00+08:00",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(signals, [])
        # Unknown types are 'skipped' — no marker, but also no signal.
        # We don't write markers for skipped events so they can be re-evaluated
        # if event_type mappings expand.
        marker = path.with_suffix(path.suffix + ".processed")
        self.assertFalse(marker.exists())

    def test_signal_id_under_64_chars(self) -> None:
        """Anthropic Batch API custom_id limit is 64 chars."""
        long_uuid = "beae7e34-d1e7-4708-8583-0ca13a0630c1"  # 36 chars
        long_filename = "subagent_done_20260509T184432_0b092333.json"  # 41 chars stem
        self._write_session_header(long_uuid, {
            "session_id": long_uuid, "cwd": "/repo", "transcript_path": "/repo/t.jsonl",
            "source": "startup", "model": "claude-opus-4-7",
            "started_at": "2026-05-09T18:00:00+08:00",
        })
        self._write_event(long_uuid, long_filename, {
            "event_type": "subagent_done",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "agent_id": "abc12345",
            "agent_type": "general-purpose",
            "last_assistant_message": "task done",
        })
        signals = bridge.capture("2026-05-09")
        self.assertEqual(len(signals), 1)
        self.assertLessEqual(len(signals[0]["id"]), 64,
            f"signal id too long: {signals[0]['id']!r}")

    def test_signal_id_stable_across_runs(self) -> None:
        self._write_event("sess1", "prompt_a_b.json", {
            "event_type": "prompt",
            "captured_at": "2026-05-09T18:00:00+08:00",
            "prompt_text": "hi",
        })
        first_signals = bridge.capture("2026-05-09")
        # Reset markers to simulate re-run
        for marker in self.cc_dir.rglob("*.processed"):
            marker.unlink()
        second_signals = bridge.capture("2026-05-09")
        self.assertEqual(first_signals[0]["id"], second_signals[0]["id"])


if __name__ == "__main__":
    unittest.main()
