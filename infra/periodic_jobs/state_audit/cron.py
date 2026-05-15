"""state_audit.cron — 18:30 silent backstop.

Runs `git fetch --all`, then `core.audit()`, then writes outputs:
- `inbox/captured/<date>_state_audit.md` — human-readable, only when findings non-empty
- `raw_signals/<date>/state_audit.json` — observer input, always written

No notifications. No git mutations beyond `fetch`. Atomic writes.

Usage:
    python -m infra.periodic_jobs.state_audit.cron [YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import core
from .core import AuditReport, REPO_ROOT

# infra.state lives at repo root; ensure it's importable when run as a script
sys.path.insert(0, str(REPO_ROOT))
from infra.state import update_role_state, write_run_log  # noqa: E402

ROLE = "state_audit"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] state_audit.cron: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("state_audit.cron")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _fetch_all(repo: Path = REPO_ROOT) -> None:
    try:
        subprocess.run(
            ["git", "fetch", "--all", "--quiet"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        logger.warning("git fetch timed out; proceeding with stale remote state")


def _format_finding_line(f: core.Finding, today: str) -> str:
    kind = f.kind
    detail = f.detail
    if kind == "dirty_working_tree":
        n = detail.get("file_count", 0)
        return f"- **dirty_working_tree**：工作樹有 {n} 個未提交檔案。建議：{f.suggested_action}"
    if kind == "unmerged_content_branch":
        branch = detail.get("branch", "?")
        if detail.get("is_today"):
            return (
                f"- **unmerged_content_branch (today)**：`{branch}` 尚未合併。"
                f"⚠️ observer 即將於 20:00 執行，請於該時刻之前合入 main，否則今日工作不會被觀察。"
            )
        return (
            f"- **unmerged_content_branch (legacy)**：`{branch}` 為前日遺留未合併分支。"
            f"建議：{f.suggested_action}"
        )
    if kind == "stale_active_project_bridge":
        name = detail.get("project_name", "?")
        return (
            f"- **stale_active_project_bridge**：`{name}` 的 PROJECT.md 比最新 work_log 新，"
            f"observer 看不到最新進度。建議：{f.suggested_action}"
        )
    if kind == "unpushed_branch":
        branch = detail.get("branch", "?")
        ahead = detail.get("ahead", "?")
        return (
            f"- **unpushed_branch**：`{branch}` 領先 upstream {ahead} 個 commit。"
            f"建議：{f.suggested_action}"
        )
    if kind == "no_upstream":
        branch = detail.get("branch", "?")
        return f"- **no_upstream**：`{branch}` 從未 push。建議：{f.suggested_action}"
    if kind == "diverged_from_upstream":
        branch = detail.get("branch", "?")
        ahead = detail.get("ahead", "?")
        behind = detail.get("behind", "?")
        return (
            f"- **diverged_from_upstream**：`{branch}` 與 upstream 雙向分歧"
            f"（ahead={ahead}, behind={behind}）。建議：{f.suggested_action}"
        )
    if kind == "untracked_remote_branch":
        branch = detail.get("branch", "?")
        relation = detail.get("relation", "?")
        if relation == "equal":
            descr = (
                f"`{branch}` 本地無 tracking 但 origin 已有同名分支，本地與 origin 同 SHA。"
                f"補 tracking 即可。"
            )
        elif relation == "ahead":
            descr = (
                f"`{branch}` 本地無 tracking 但 origin 已有同名分支，本地領先 origin。"
                f"可 push -u 同步補 tracking。"
            )
        elif relation == "behind":
            descr = (
                f"`{branch}` 本地無 tracking 但 origin 已有同名分支，本地落後 origin。"
                f"可用 `git branch -f` 同步補 tracking + fast-forward。"
            )
        else:
            descr = (
                f"`{branch}` 本地無 tracking，origin 已有同名分支，雙向 diverged。"
                f"需手動處理。"
            )
        return f"- **untracked_remote_branch**：{descr}建議：{f.suggested_action}"
    if kind == "branch_behind_origin":
        branch = detail.get("branch", "?")
        behind = detail.get("behind_count", "?")
        is_current = detail.get("is_current", False)
        if is_current:
            return (
                f"- **branch_behind_origin (current)**：current branch `{branch}` 落後 "
                f"origin/{branch} {behind} 個 commit。不能用 `git branch -f` 對 current "
                f"branch 操作。建議：{f.suggested_action}"
            )
        return (
            f"- **branch_behind_origin**：`{branch}` 落後 origin/{branch} {behind} "
            f"個 commit。建議：{f.suggested_action}"
        )
    if kind == "missed_observer_run":
        expected = detail.get("expected_date", "?")
        return (
            f"- **missed_observer_run**：observer 預期於 {expected} 跑但 raw_signals 找不到 run log。"
            f"建議：{f.suggested_action}"
        )
    if kind == "missed_reflector_run":
        last = detail.get("last_finished_at") or "從未記錄"
        return (
            f"- **missed_reflector_run**：reflector last_finished_at={last}，超過週期門檻。"
            f"建議：{f.suggested_action}"
        )
    if kind == "stale_running_role":
        role = detail.get("role", "?")
        elapsed = detail.get("elapsed_hours", "?")
        threshold = detail.get("threshold_hours", "?")
        return (
            f"- **stale_running_role**：`{role}` 卡 last_status=running 已 {elapsed}h"
            f"（閾值 {threshold}h）。建議：{f.suggested_action}"
        )
    return f"- **{kind}**：{detail}"


def write_inbox_summary(report: AuditReport, target_date: str, repo: Path = REPO_ROOT) -> Path | None:
    """Write inbox/captured/<date>_state_audit.md when findings non-empty.

    Returns the path written, or None if findings empty.
    """
    if not report.findings:
        return None

    path = repo / "inbox" / "captured" / f"{target_date}_state_audit.md"
    lines = [
        f"# State Audit — {target_date}",
        "",
        f"_由 `state_audit/cron.py` 在 {report.timestamp} 寫入。當前分支：`{report.branch}`。_",
        "",
        f"共 {len(report.findings)} 項 findings：",
        "",
    ]
    for f in report.findings:
        lines.append(_format_finding_line(f, target_date))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("處理建議：執行 `/ctx:eod` 進入下班總整理流程。")
    lines.append("")
    _atomic_write(path, "\n".join(lines))
    return path


def write_raw_signal(report: AuditReport, target_date: str, repo: Path = REPO_ROOT) -> Path:
    """Always write raw_signals/<date>/state_audit.json (atomic)."""
    path = repo / "raw_signals" / target_date / "state_audit.json"
    _atomic_write(path, report.to_json() + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="state_audit silent backstop")
    parser.add_argument(
        "date",
        nargs="?",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Target date (YYYY-MM-DD), defaults to today",
    )
    args = parser.parse_args()
    target_date = args.date

    started_at = _now_iso()
    update_role_state(
        ROLE,
        last_started_at=started_at,
        last_target_date=target_date,
        last_status="running",
        last_finished_at=None,
    )

    try:
        _fetch_all()
        report = core.audit(today=target_date)

        raw_path = write_raw_signal(report, target_date)
        logger.info("raw_signal written: %s (findings=%d)", raw_path, len(report.findings))

        inbox_path = write_inbox_summary(report, target_date)
        if inbox_path:
            logger.info("inbox summary written: %s", inbox_path)
        else:
            logger.info("no findings; inbox summary skipped")
    except Exception as e:
        finished_at = _now_iso()
        error_summary = f"{type(e).__name__}: {e}"
        update_role_state(ROLE, last_finished_at=finished_at, last_status="failed")
        write_run_log(
            role=ROLE,
            target_date=target_date,
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            error_summary=error_summary,
        )
        traceback.print_exc()
        return 1

    finished_at = _now_iso()
    update_role_state(ROLE, last_finished_at=finished_at, last_status="ok")
    write_run_log(
        role=ROLE,
        target_date=target_date,
        started_at=started_at,
        finished_at=finished_at,
        status="ok",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
