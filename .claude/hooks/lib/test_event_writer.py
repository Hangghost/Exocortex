"""
Minimal unit test for event_writer. Run with:

    python -m unittest .claude.hooks.lib.test_event_writer

Or directly:

    python .claude/hooks/lib/test_event_writer.py

Tests use a temp dir override so they don't touch real inbox/captured/cc_events/.
"""
import json
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Make .claude/hooks/lib importable when running directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.lib import event_writer  # noqa: E402


class WriteEventTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self._cc_patch = patch.object(
            event_writer, "CC_EVENTS_DIR", self.tmp_path / "cc_events"
        )
        self._fb_patch = patch.object(
            event_writer, "FALLBACK_LOG_DIR", self.tmp_path / "fallback"
        )
        self._cc_patch.start()
        self._fb_patch.start()

    def tearDown(self) -> None:
        self._cc_patch.stop()
        self._fb_patch.stop()
        self.tmp.cleanup()

    def test_writes_prompt_event_with_envelope(self) -> None:
        path = event_writer.write_event(
            "prompt",
            "abc-123",
            {"prompt_text": "hello"},
        )
        self.assertIsNotNone(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["event_type"], "prompt")
        self.assertEqual(data["prompt_text"], "hello")
        self.assertIn("captured_at", data)
        # session_id is for directory location, not embedded in event JSON
        self.assertNotIn("session_id", data)
        # cwd/transcript_path are session-level, in session.json header
        self.assertNotIn("cwd", data)
        self.assertNotIn("transcript_path", data)
        # but the file is still under <session_id>/
        self.assertEqual(path.parent.name, "abc-123")

    def test_filename_includes_ts_and_uuid(self) -> None:
        path = event_writer.write_event("prompt", "sess", {"prompt_text": "x"})
        self.assertIsNotNone(path)
        # prompt_<ts>_<uuid>.json — three parts after split by "_"
        name = path.name
        self.assertTrue(name.startswith("prompt_"))
        self.assertTrue(name.endswith(".json"))
        parts = name.replace(".json", "").split("_")
        self.assertEqual(len(parts), 3)

    def test_consecutive_writes_no_collision(self) -> None:
        p1 = event_writer.write_event("prompt", "sess", {"prompt_text": "1"})
        p2 = event_writer.write_event("prompt", "sess", {"prompt_text": "2"})
        self.assertNotEqual(p1, p2)
        self.assertTrue(p1.exists() and p2.exists())

    def test_fixed_filename_overrides_generated(self) -> None:
        path = event_writer.write_event(
            "session_done",
            "sess",
            {"reason": "exit"},
            fixed_filename="_session_done.json",
        )
        self.assertEqual(path.name, "_session_done.json")

    def test_unknown_session_id_falls_back(self) -> None:
        path = event_writer.write_event("prompt", None, {"prompt_text": "x"})
        self.assertIsNotNone(path)
        self.assertEqual(path.parent.name, "unknown")

    def test_dangerous_session_id_sanitized(self) -> None:
        path = event_writer.write_event("prompt", "../../etc", {"prompt_text": "x"})
        self.assertIsNotNone(path)
        self.assertNotIn("..", str(path.parent))

    def test_failure_writes_fallback_log(self) -> None:
        # Force a failure by patching json.dumps to raise.
        with patch("json.dumps", side_effect=RuntimeError("boom")):
            path = event_writer.write_event("prompt", "sess", {"prompt_text": "x"})
        self.assertIsNone(path)
        # Fallback log directory should exist with a log file.
        log_files = list((self.tmp_path / "fallback").glob("*.log"))
        self.assertEqual(len(log_files), 1)
        self.assertIn("boom", log_files[0].read_text(encoding="utf-8"))

    def test_read_payload_from_stdin_parses_json(self) -> None:
        payload = {"foo": "bar"}
        with patch("sys.stdin", io.StringIO(json.dumps(payload))):
            result = event_writer.read_payload_from_stdin()
        self.assertEqual(result, payload)

    def test_read_payload_from_stdin_returns_empty_on_garbage(self) -> None:
        with patch("sys.stdin", io.StringIO("not json")):
            result = event_writer.read_payload_from_stdin()
        self.assertEqual(result, {})


class WriteSessionHeaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self._cc_patch = patch.object(
            event_writer, "CC_EVENTS_DIR", self.tmp_path / "cc_events"
        )
        self._fb_patch = patch.object(
            event_writer, "FALLBACK_LOG_DIR", self.tmp_path / "fallback"
        )
        self._cc_patch.start()
        self._fb_patch.start()

    def tearDown(self) -> None:
        self._cc_patch.stop()
        self._fb_patch.stop()
        self.tmp.cleanup()

    def test_writes_session_json_with_header_fields(self) -> None:
        header = {
            "session_id": "sess-1",
            "cwd": "/repo",
            "transcript_path": "/repo/t.jsonl",
            "source": "startup",
            "model": "claude-opus-4-7",
            "started_at": "2026-05-10T08:00:00+08:00",
        }
        path = event_writer.write_session_header("sess-1", header)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "session.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data, header)

    def test_resume_overwrites_existing_session_json(self) -> None:
        first = {
            "session_id": "sess-1",
            "cwd": "/repo",
            "transcript_path": "/repo/t.jsonl",
            "source": "startup",
            "model": "claude-opus-4-7",
            "started_at": "2026-05-10T08:00:00+08:00",
        }
        event_writer.write_session_header("sess-1", first)

        second = {**first, "source": "resume", "started_at": "2026-05-10T09:30:00+08:00"}
        path = event_writer.write_session_header("sess-1", second)
        self.assertIsNotNone(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["source"], "resume")
        self.assertEqual(data["started_at"], "2026-05-10T09:30:00+08:00")
        # Single file: no ts/uuid suffix variants
        files = list(path.parent.glob("session*.json"))
        self.assertEqual(len(files), 1)

    def test_failure_writes_fallback_log(self) -> None:
        with patch("json.dumps", side_effect=RuntimeError("boom")):
            path = event_writer.write_session_header("sess", {"source": "startup"})
        self.assertIsNone(path)
        log_files = list((self.tmp_path / "fallback").glob("*.log"))
        self.assertEqual(len(log_files), 1)
        self.assertIn("session_header", log_files[0].read_text(encoding="utf-8"))

    def test_unknown_session_id_falls_back(self) -> None:
        path = event_writer.write_session_header(None, {"source": "startup"})
        self.assertIsNotNone(path)
        self.assertEqual(path.parent.name, "unknown")


class ResolveMainRepoRootTest(unittest.TestCase):
    """
    Test _resolve_main_repo_root: walks up to find .git, handling both
    main-repo (.git is a directory) and worktree (.git is a file with
    `gitdir:` pointer) cases.
    """

    def test_resolves_main_repo_when_git_is_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "myrepo"
            (repo / ".git").mkdir(parents=True)
            (repo / "subdir" / "deeper").mkdir(parents=True)
            self.assertEqual(
                event_writer._resolve_main_repo_root(repo / "subdir" / "deeper"),
                repo.resolve(),
            )

    def test_resolves_main_repo_from_worktree_via_gitdir_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main_repo = Path(tmp) / "main"
            (main_repo / ".git" / "worktrees" / "wt-name").mkdir(parents=True)
            worktree = Path(tmp) / "main" / ".claude" / "worktrees" / "wt-name"
            worktree.mkdir(parents=True)
            (worktree / ".git").write_text(
                f"gitdir: {main_repo / '.git' / 'worktrees' / 'wt-name'}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                event_writer._resolve_main_repo_root(worktree),
                main_repo.resolve(),
            )

    def test_malformed_git_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wt = Path(tmp) / "wt"
            wt.mkdir()
            (wt / ".git").write_text("garbage with no gitdir line\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                event_writer._resolve_main_repo_root(wt)

    def test_no_git_above_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                event_writer._resolve_main_repo_root(Path(tmp))

    def test_module_level_REPO_ROOT_is_path(self) -> None:
        # Validates that the try/except fallback at module load did not blow up
        # — REPO_ROOT must be set to a Path no matter what.
        self.assertIsInstance(event_writer.REPO_ROOT, Path)


class CaptureUserPromptFilterTest(unittest.TestCase):
    """Test the system-injection filter in capture_user_prompt.py."""

    def setUp(self) -> None:
        # Make sibling capture_user_prompt importable.
        hooks_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(hooks_dir))

    def test_genuine_user_prompt_not_filtered(self) -> None:
        from capture_user_prompt import _is_system_injected
        self.assertFalse(_is_system_injected("hello world"))
        self.assertFalse(_is_system_injected("不對"))
        self.assertFalse(_is_system_injected("/opsx:apply add-foo"))

    def test_task_notification_filtered(self) -> None:
        from capture_user_prompt import _is_system_injected
        payload = "<task-notification>\n<task-id>abc</task-id>\n</task-notification>"
        self.assertTrue(_is_system_injected(payload))

    def test_system_notification_marker_filtered(self) -> None:
        from capture_user_prompt import _is_system_injected
        payload = "[SYSTEM NOTIFICATION - NOT USER INPUT]\nbackground task done"
        self.assertTrue(_is_system_injected(payload))

    def test_marker_with_leading_whitespace_filtered(self) -> None:
        from capture_user_prompt import _is_system_injected
        payload = "\n\n  <task-notification>foo</task-notification>"
        self.assertTrue(_is_system_injected(payload))

    def test_marker_after_500_chars_not_filtered(self) -> None:
        # If the marker appears far down the prompt body, it's likely the user
        # quoting a notification, not CC injecting one. Don't filter.
        from capture_user_prompt import _is_system_injected
        prefix = "user typed text " * 50  # ~ 800 chars
        payload = prefix + "<task-notification>"
        self.assertFalse(_is_system_injected(payload))

    def test_empty_prompt_not_filtered(self) -> None:
        from capture_user_prompt import _is_system_injected
        self.assertFalse(_is_system_injected(""))


if __name__ == "__main__":
    unittest.main()
