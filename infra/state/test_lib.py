"""Unit tests for infra.state.lib.

Run:
    python -m unittest infra.state.test_lib -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from . import lib
from .lib import (
    SYSTEM_STATE_VERSION,
    StateError,
    read_system_state,
    role_last_run,
    update_role_state,
    write_run_log,
)


class StateLibTestBase(unittest.TestCase):
    """Redirects SYSTEM_STATE_PATH and RAW_SIGNALS_DIR into a tmpdir.

    Each test runs against a clean filesystem layout so that earlier
    writes don't leak across tests.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)
        self.state_path = self._tmp_path / "infra" / "state" / "system_state.json"
        self.raw_dir = self._tmp_path / "raw_signals"

        self._orig_state_path = lib.SYSTEM_STATE_PATH
        self._orig_raw_dir = lib.RAW_SIGNALS_DIR
        lib.SYSTEM_STATE_PATH = self.state_path
        lib.RAW_SIGNALS_DIR = self.raw_dir

    def tearDown(self) -> None:
        lib.SYSTEM_STATE_PATH = self._orig_state_path
        lib.RAW_SIGNALS_DIR = self._orig_raw_dir
        self._tmp.cleanup()


class TestReadSystemState(StateLibTestBase):
    def test_returns_none_when_missing(self) -> None:
        self.assertFalse(self.state_path.exists())
        self.assertIsNone(read_system_state())

    def test_returns_none_when_malformed_json(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text("not json {", encoding="utf-8")
        self.assertIsNone(read_system_state())

    def test_returns_none_on_unknown_version(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(
            json.dumps({"version": 999, "roles": {}}), encoding="utf-8"
        )
        self.assertIsNone(read_system_state())

    def test_returns_none_when_roles_missing(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(
            json.dumps({"version": SYSTEM_STATE_VERSION}), encoding="utf-8"
        )
        self.assertIsNone(read_system_state())

    def test_returns_dict_on_valid(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(
            json.dumps(
                {
                    "version": SYSTEM_STATE_VERSION,
                    "roles": {"observer": {"last_status": "ok"}},
                }
            ),
            encoding="utf-8",
        )
        state = read_system_state()
        assert state is not None
        self.assertEqual(state["roles"]["observer"]["last_status"], "ok")


class TestUpdateRoleState(StateLibTestBase):
    def test_creates_file_when_missing(self) -> None:
        update_role_state(
            "observer",
            last_started_at="2026-05-01T20:00:00+08:00",
            last_status="running",
            last_target_date="2026-05-01",
        )
        self.assertTrue(self.state_path.exists())
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["version"], SYSTEM_STATE_VERSION)
        self.assertEqual(state["roles"]["observer"]["last_status"], "running")

    def test_merges_into_existing_role(self) -> None:
        update_role_state("observer", last_status="running")
        update_role_state(
            "observer",
            last_status="ok",
            last_finished_at="2026-05-01T20:01:42+08:00",
        )
        state = read_system_state()
        assert state is not None
        self.assertEqual(state["roles"]["observer"]["last_status"], "ok")
        self.assertEqual(
            state["roles"]["observer"]["last_finished_at"],
            "2026-05-01T20:01:42+08:00",
        )

    def test_preserves_other_roles(self) -> None:
        update_role_state("observer", last_status="ok")
        update_role_state("reflector", last_status="ok")
        state = read_system_state()
        assert state is not None
        self.assertIn("observer", state["roles"])
        self.assertIn("reflector", state["roles"])

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(StateError):
            update_role_state("observer", last_status="weird")

    def test_recovers_from_malformed_file(self) -> None:
        """Malformed file gets overwritten, not propagated."""
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text("garbage", encoding="utf-8")
        update_role_state("observer", last_status="ok")
        state = read_system_state()
        assert state is not None
        self.assertEqual(state["roles"]["observer"]["last_status"], "ok")


class TestRoleLastRun(StateLibTestBase):
    def test_returns_none_when_state_missing(self) -> None:
        self.assertIsNone(role_last_run("observer"))

    def test_returns_none_when_role_missing(self) -> None:
        update_role_state("observer", last_status="ok")
        self.assertIsNone(role_last_run("reflector"))

    def test_returns_role_dict(self) -> None:
        update_role_state(
            "observer", last_status="ok", last_target_date="2026-05-01"
        )
        role = role_last_run("observer")
        assert role is not None
        self.assertEqual(role["last_status"], "ok")
        self.assertEqual(role["last_target_date"], "2026-05-01")


class TestWriteRunLog(StateLibTestBase):
    def test_creates_file(self) -> None:
        path = write_run_log(
            role="observer",
            target_date="2026-05-01",
            started_at="2026-05-01T20:00:00+08:00",
            finished_at="2026-05-01T20:01:42+08:00",
            status="ok",
            session_id="abc",
        )
        expected = self.raw_dir / "2026-05-01" / "observer_run.json"
        self.assertEqual(path, expected)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "observer_run")
        self.assertEqual(payload["session_id"], "abc")
        self.assertEqual(payload["status"], "ok")

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(StateError):
            write_run_log(
                role="observer",
                target_date="2026-05-01",
                started_at="2026-05-01T20:00:00+08:00",
                finished_at=None,
                status="bogus",
            )

    def test_supports_failure_payload(self) -> None:
        path = write_run_log(
            role="observer",
            target_date="2026-05-01",
            started_at="2026-05-01T20:00:00+08:00",
            finished_at="2026-05-01T20:00:05+08:00",
            status="failed",
            error_summary="boom",
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error_summary"], "boom")


class TestAtomicWrite(StateLibTestBase):
    def test_no_tmp_file_left_on_success(self) -> None:
        update_role_state("observer", last_status="ok")
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        self.assertFalse(tmp.exists())

    def test_keeps_old_content_when_replace_fails(self) -> None:
        """If os.replace raises, the original file should remain intact."""
        update_role_state("observer", last_status="ok")
        original = self.state_path.read_text(encoding="utf-8")

        orig_replace = lib.os.replace

        def boom(*args, **kwargs):
            raise OSError("simulated replace failure")

        lib.os.replace = boom
        try:
            with self.assertRaises(OSError):
                update_role_state("observer", last_status="failed")
        finally:
            lib.os.replace = orig_replace

        self.assertEqual(
            self.state_path.read_text(encoding="utf-8"), original
        )


if __name__ == "__main__":
    unittest.main()
