"""verify_clean_scenario.py — 一次性 harness：驗證「乾淨」情境。

為 add-state-audit change 的 task 7.2 補上「乾淨情境」覆蓋（真實 repo 永遠髒，
無法用 /ctx:eod 觸發此路徑）。在 /tmp 建一個無 finding 的 fixture，跑完
core.audit() + cron.write_*，確認：

1. audit() 對乾淨 fixture 回傳 findings == []
2. write_inbox_summary 在 findings 為空時不寫檔（回 None）
3. write_raw_signal 永遠寫檔，且內容 findings 陣列為空

驗證完成後可刪除此檔（或保留作為 manual smoke test）。

Run:
    python -m infra.periodic_jobs.state_audit.verify_clean_scenario
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import core, cron


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def init_clean_fixture() -> tuple[Path, Path]:
    base = Path(tempfile.mkdtemp(prefix="state_audit_clean_"))
    bare = base / "remote.git"
    work = base / "work"

    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(bare)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main", str(work)],
        check=True, capture_output=True, text=True,
    )

    _git(work, "config", "user.email", "verify@local")
    _git(work, "config", "user.name", "Verify")

    (work / "README.md").write_text("clean fixture\n", encoding="utf-8")
    _git(work, "add", "README.md")
    _git(work, "commit", "-q", "-m", "init")

    _git(work, "remote", "add", "origin", str(bare))
    _git(work, "push", "-u", "-q", "origin", "main")

    return base, work


def main() -> int:
    base, work = init_clean_fixture()
    failures: list[str] = []

    try:
        report = core.audit(repo=work, today="2026-05-01")

        if report.findings:
            kinds = [f.kind for f in report.findings]
            failures.append(
                f"audit() 預期 0 findings，實得 {len(report.findings)}: {kinds}"
            )
        else:
            print("PASS [1/3] audit() 對乾淨 fixture 回傳 0 findings")

        inbox_path = cron.write_inbox_summary(report, "2026-05-01", repo=work)
        if inbox_path is not None:
            failures.append(
                f"write_inbox_summary 預期 None（findings 為空），實得 {inbox_path}"
            )
        elif (work / "inbox" / "captured" / "2026-05-01_state_audit.md").exists():
            failures.append("write_inbox_summary 不應寫檔，但檔案存在")
        else:
            print("PASS [2/3] write_inbox_summary 在 findings 為空時 skip 寫檔")

        raw_path = cron.write_raw_signal(report, "2026-05-01", repo=work)
        if not raw_path.exists():
            failures.append(f"write_raw_signal 應寫檔，但檔案不存在: {raw_path}")
        else:
            data = json.loads(raw_path.read_text(encoding="utf-8"))
            if data.get("findings") != []:
                failures.append(
                    f"raw_signal findings 預期 []，實得 {data.get('findings')}"
                )
            else:
                print("PASS [3/3] write_raw_signal 永遠寫檔，且 findings 為空陣列")

    finally:
        shutil.rmtree(base, ignore_errors=True)

    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED — 乾淨情境驗證通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
