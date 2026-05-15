"""Tests for state_audit.cron output behavior.

Verifies:
- findings empty → only raw_signals written, inbox skipped
- findings non-empty → both written
- atomic write leaves no .tmp file
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from . import core, cron


class CronOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="state_audit_cron_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_findings_writes_raw_only(self) -> None:
        report = core.AuditReport(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            branch="main",
            findings=[],
        )
        date = "2026-05-01"
        raw = cron.write_raw_signal(report, date, repo=self.tmp)
        inbox = cron.write_inbox_summary(report, date, repo=self.tmp)

        self.assertTrue(raw.exists())
        data = json.loads(raw.read_text(encoding="utf-8"))
        self.assertEqual(data["findings"], [])
        self.assertIsNone(inbox)
        self.assertFalse((self.tmp / "inbox" / "captured" / f"{date}_state_audit.md").exists())

    def test_non_empty_findings_writes_both(self) -> None:
        report = core.AuditReport(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            branch="content/2026-05-01",
            findings=[
                core.Finding(
                    kind="dirty_working_tree",
                    severity="warn",
                    detail={"file_count": 3, "sample": ["?? a", "?? b"]},
                    suggested_action="跑 /ctx:content",
                )
            ],
        )
        date = "2026-05-01"
        cron.write_raw_signal(report, date, repo=self.tmp)
        inbox = cron.write_inbox_summary(report, date, repo=self.tmp)

        self.assertIsNotNone(inbox)
        self.assertTrue(inbox.exists())
        text = inbox.read_text(encoding="utf-8")
        self.assertIn("dirty_working_tree", text)
        self.assertIn("content/2026-05-01", text)

    def test_atomic_write_leaves_no_tmp(self) -> None:
        report = core.AuditReport(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            branch="main",
            findings=[],
        )
        cron.write_raw_signal(report, "2026-05-01", repo=self.tmp)
        for tmp in self.tmp.rglob("*.tmp"):
            self.fail(f"left orphan tmp file: {tmp}")

    def test_today_unmerged_content_distinguishes_prose(self) -> None:
        report = core.AuditReport(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            branch="main",
            findings=[
                core.Finding(
                    kind="unmerged_content_branch",
                    severity="info",
                    detail={"branch": "content/2026-05-01", "date": "2026-05-01", "is_today": True, "sha": "x"},
                ),
                core.Finding(
                    kind="unmerged_content_branch",
                    severity="warn",
                    detail={"branch": "content/2026-04-30", "date": "2026-04-30", "is_today": False, "sha": "y"},
                ),
            ],
        )
        inbox = cron.write_inbox_summary(report, "2026-05-01", repo=self.tmp)
        text = inbox.read_text(encoding="utf-8")
        self.assertIn("(today)", text)
        self.assertIn("observer 即將於 20:00", text)
        self.assertIn("(legacy)", text)


if __name__ == "__main__":
    unittest.main()
