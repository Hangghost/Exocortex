"""state_audit.core — 純規則性的儲存庫狀態審計。

`audit() -> AuditReport` 為共用進入點，給 `cron.py` 與 `/ctx:eod` 命令使用。
所有檢查皆透過 `subprocess` 呼叫 `git`，不依賴 GitPython 或其他第三方庫。

設計參考：`openspec/changes/add-state-audit/design.md`
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[3]

logger = logging.getLogger("state_audit.core")

FindingKind = Literal[
    "dirty_working_tree",
    "unmerged_content_branch",
    "stale_active_project_bridge",
    "unpushed_branch",
    "no_upstream",
    "diverged_from_upstream",
    "untracked_remote_branch",
    "branch_behind_origin",
    "missed_observer_run",
    "missed_reflector_run",
    "role_failed_run",
    "stale_running_role",
]

# Reflector runs weekly; if last_finished_at is older than this, treat as
# "should have run by now". 8 days gives one slack day for late catch-ups.
REFLECTOR_STALENESS_DAYS = 8

# A role is considered "stale running" when last_status="running" and
# last_started_at is older than this. Catches uncontrollable kills (SIGKILL,
# crashes, hardware loss) that bypass the role's atexit/SIGTERM finalization.
RUNNING_THRESHOLD_HOURS = 2.0

ROLE_RECOVERY_HINTS: dict[str, str] = {
    "observer": (
        "補跑 observer：python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe <date>"
    ),
    "reflector": (
        "補跑 reflector：python infra/periodic_jobs/ai_heartbeat/src/v0/reflector.py"
    ),
}

_GENERIC_FAILED_HINT_TEMPLATE = (
    "查 raw_signals/<date>/{role}_run.json 取得失敗詳情；視需要手動補跑該 role"
)

# stale_running_role 對應的 hint：與 role_failed_run 拆開的原因是
# stale running 的根因可能是 process 被 kill、磁碟滿、SIGKILL；提示文字
# 必須警示「不要對 system_state.json 跑 git checkout -- revert」——
# running 狀態可能對應未收尾的真實 cron 工作，revert 會清掉真實產出。
ROLE_STALE_RUNNING_HINTS: dict[str, str] = {
    "observer": (
        "Observer 卡 running 過久，可能 process 被 kill 未收尾。手動補跑：\n"
        "  .venv/bin/python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe <date>\n"
        "⚠️ 不要對 infra/state/system_state.json 跑 git checkout -- 直接 revert——"
        "running 狀態可能對應未收尾的真實 cron 工作（OBSERVATIONS.md 等已寫入的產出），"
        "revert 會清掉真實工作。"
    ),
    "capture": (
        "Capture 卡 running 過久。手動補跑：\n"
        "  .venv/bin/python -m infra.periodic_jobs.ai_heartbeat.src.v1.capture <date>\n"
        "⚠️ 不要對 system_state.json 跑 git checkout -- 直接 revert。"
    ),
    "triage_stage1": (
        "Triage stage1 卡 running 過久。手動補跑：\n"
        "  .venv/bin/python -m infra.periodic_jobs.ai_heartbeat.src.v1.triage.stage1 <date>"
    ),
    "triage_stage2": (
        "Triage stage2 卡 running 過久。手動補跑：\n"
        "  .venv/bin/python -m infra.periodic_jobs.ai_heartbeat.src.v1.triage.stage2 <date>"
    ),
    "reflector": (
        "Reflector 卡 running 過久。手動補跑：\n"
        "  python infra/periodic_jobs/ai_heartbeat/src/v0/reflector.py"
    ),
}

_GENERIC_STALE_RUNNING_HINT_TEMPLATE = (
    "{role} 卡 running 超過 {elapsed:.1f}h（閾值 {threshold:.1f}h）。"
    "process 可能已終止但 state 未收尾；查 raw_signals/<date>/{role}_run.json 確認。"
    "⚠️ 不要對 system_state.json 跑 git checkout -- 直接 revert。"
)

Severity = Literal["info", "warn", "block"]

WELL_FORMED_PREFIXES = ("content/", "project/", "feature/")
WELL_FORMED_BRANCHES = {"main", "master"}

CONTENT_BRANCH_RE = re.compile(r"^content/(\d{4}-\d{2}-\d{2})$")


@dataclass
class Finding:
    kind: FindingKind
    severity: Severity
    detail: dict[str, Any]
    suggested_action: str | None = None


@dataclass
class AuditReport:
    timestamp: str
    branch: str
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "branch": self.branch,
            "findings": [asdict(f) for f in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# git wrappers
# ---------------------------------------------------------------------------


def _git(*args: str, repo: Path = REPO_ROOT, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_ok(*args: str, repo: Path = REPO_ROOT) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _current_branch(repo: Path = REPO_ROOT) -> str:
    return _git("branch", "--show-current", repo=repo).strip() or "HEAD"


def _git_mtime(path: str, repo: Path = REPO_ROOT) -> int:
    """Return the latest commit time (unix seconds) for `path`. 0 if unknown."""
    out = _git("log", "-1", "--format=%ct", "--", path, repo=repo).strip()
    return int(out) if out else 0


def _commit_in_ancestry(commit: str, ref: str, repo: Path = REPO_ROOT) -> bool:
    """True iff `commit` is an ancestor of `ref` (i.e. already merged)."""
    code, _, _ = _git_ok("merge-base", "--is-ancestor", commit, ref, repo=repo)
    return code == 0


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def _check_dirty_working_tree(repo: Path = REPO_ROOT) -> list[Finding]:
    out = _git("status", "--porcelain", repo=repo)
    if not out.strip():
        return []
    lines = [line for line in out.splitlines() if line.strip()]
    return [
        Finding(
            kind="dirty_working_tree",
            severity="warn",
            detail={"file_count": len(lines), "sample": lines[:5]},
            suggested_action="跑 /ctx:content 提交，或手動 git stash",
        )
    ]


def _check_unmerged_content_branches(
    today: str | None = None, repo: Path = REPO_ROOT
) -> list[Finding]:
    today = today or datetime.now().strftime("%Y-%m-%d")
    raw = _git(
        "for-each-ref",
        "--format=%(refname:short) %(objectname)",
        "refs/heads/content/",
        repo=repo,
    )
    findings: list[Finding] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        branch, sha = parts
        m = CONTENT_BRANCH_RE.match(branch)
        if not m:
            continue
        date_str = m.group(1)
        if _commit_in_ancestry(sha, "main", repo=repo):
            continue
        is_today = date_str == today
        findings.append(
            Finding(
                kind="unmerged_content_branch",
                severity="info" if is_today else "warn",
                detail={
                    "branch": branch,
                    "date": date_str,
                    "is_today": is_today,
                    "sha": sha,
                },
                suggested_action=(
                    "今日仍在累積（caller policy 決定是否提醒）"
                    if is_today
                    else "考慮 /ctx:content merge 合入 main"
                ),
            )
        )
    return findings


def _list_active_projects(repo: Path = REPO_ROOT) -> list[str]:
    index = repo / "projects" / "INDEX.md"
    if not index.exists():
        return []
    names: list[str] = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        name, status = cells[0], cells[1]
        if status == "active":
            names.append(name)
    return names


def _latest_work_log_mtime(name: str, repo: Path = REPO_ROOT) -> int:
    work_logs = repo / "contexts" / "work_logs"
    if not work_logs.exists():
        return 0
    latest = 0
    for path in work_logs.iterdir():
        if not path.is_file():
            continue
        n = path.name
        if not (n.endswith(f"{name}_update.md") or n.endswith(f"{name}_retrospective.md")):
            continue
        rel = path.relative_to(repo).as_posix()
        ts = _git_mtime(rel, repo=repo)
        if ts > latest:
            latest = ts
    return latest


def _check_stale_active_project_bridges(repo: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for name in _list_active_projects(repo=repo):
        project_md = repo / "projects" / name / "PROJECT.md"
        if not project_md.exists():
            continue
        rel = project_md.relative_to(repo).as_posix()
        project_mtime = _git_mtime(rel, repo=repo)
        log_mtime = _latest_work_log_mtime(name, repo=repo)
        if project_mtime > log_mtime:
            findings.append(
                Finding(
                    kind="stale_active_project_bridge",
                    severity="warn",
                    detail={
                        "project_name": name,
                        "project_mtime": project_mtime,
                        "latest_work_log_mtime": log_mtime,
                    },
                    suggested_action=f"/ctx:project update {name}",
                )
            )
    return findings


def _list_local_branches(repo: Path = REPO_ROOT) -> list[str]:
    raw = _git("for-each-ref", "--format=%(refname:short)", "refs/heads/", repo=repo)
    return [b.strip() for b in raw.splitlines() if b.strip()]


def _upstream(branch: str, repo: Path = REPO_ROOT) -> str | None:
    code, out, _ = _git_ok(
        "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}", repo=repo
    )
    if code != 0:
        return None
    name = out.strip()
    return name or None


def _ahead_behind(branch: str, upstream: str, repo: Path = REPO_ROOT) -> tuple[int, int]:
    code, out, _ = _git_ok(
        "rev-list", "--left-right", "--count", f"{upstream}...{branch}", repo=repo
    )
    if code != 0 or not out.strip():
        return 0, 0
    parts = out.split()
    if len(parts) != 2:
        return 0, 0
    behind, ahead = int(parts[0]), int(parts[1])
    return ahead, behind


def _is_well_formed(branch: str) -> bool:
    if branch in WELL_FORMED_BRANCHES:
        return True
    return any(branch.startswith(p) for p in WELL_FORMED_PREFIXES)


def _origin_ref_exists(branch: str, repo: Path = REPO_ROOT) -> bool:
    """True iff `refs/remotes/origin/<branch>` exists in fetched local cache.

    Caller is responsible for `git fetch` freshness; this function does not fetch.
    """
    code, _, _ = _git_ok(
        "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}", repo=repo
    )
    return code == 0


def _origin_relation(branch: str, repo: Path = REPO_ROOT) -> tuple[str, int, int]:
    """Compute local <branch> vs origin/<branch> relation.

    Returns (relation, ahead, behind) where relation in
    {"equal", "ahead", "behind", "diverged"}.
    """
    ahead, behind = _ahead_behind(branch, f"origin/{branch}", repo=repo)
    if ahead == 0 and behind == 0:
        return "equal", 0, 0
    if ahead > 0 and behind == 0:
        return "ahead", ahead, 0
    if ahead == 0 and behind > 0:
        return "behind", 0, behind
    return "diverged", ahead, behind


def _check_unpushed_branches(repo: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for branch in _list_local_branches(repo=repo):
        upstream = _upstream(branch, repo=repo)
        if upstream is None:
            if _origin_ref_exists(branch, repo=repo):
                # Untracked but remote ref already exists — likely pushed from
                # another machine. Compute relation so /ctx:eod can dispatch.
                relation, ahead, behind = _origin_relation(branch, repo=repo)
                if relation == "equal":
                    action = f"git branch --set-upstream-to=origin/{branch} {branch}"
                elif relation == "ahead":
                    action = f"git push -u origin {branch}"
                elif relation == "behind":
                    action = f"git branch -f {branch} origin/{branch}"
                else:  # diverged
                    action = "詢問 rebase / reset / skip"
                findings.append(
                    Finding(
                        kind="untracked_remote_branch",
                        severity="warn",
                        detail={
                            "branch": branch,
                            "relation": relation,
                            "ahead": ahead,
                            "behind": behind,
                            "well_formed_prefix": _is_well_formed(branch),
                        },
                        suggested_action=action,
                    )
                )
            else:
                findings.append(
                    Finding(
                        kind="no_upstream",
                        severity="warn",
                        detail={
                            "branch": branch,
                            "well_formed_prefix": _is_well_formed(branch),
                        },
                        suggested_action=(
                            f"git push -u origin {branch}"
                            if _is_well_formed(branch)
                            else f"未知前綴，詢問是否 push -u origin {branch}"
                        ),
                    )
                )
            continue
        ahead, behind = _ahead_behind(branch, upstream, repo=repo)
        if ahead > 0 and behind > 0:
            findings.append(
                Finding(
                    kind="diverged_from_upstream",
                    severity="block",
                    detail={
                        "branch": branch,
                        "upstream": upstream,
                        "ahead": ahead,
                        "behind": behind,
                    },
                    suggested_action="diverged，詢問 rebase / skip / 其他",
                )
            )
        elif ahead > 0:
            findings.append(
                Finding(
                    kind="unpushed_branch",
                    severity="info",
                    detail={
                        "branch": branch,
                        "upstream": upstream,
                        "ahead": ahead,
                        "well_formed_prefix": _is_well_formed(branch),
                    },
                    suggested_action=f"git push origin {branch}",
                )
            )
    return findings


def _check_branch_behind_origin(repo: Path = REPO_ROOT) -> list[Finding]:
    """Emit branch_behind_origin for every local branch (with upstream) that
    is strictly behind origin/<branch>. Covers main and all well-formed branches.

    No-upstream branches are covered by `_check_unpushed_branches` via the
    `untracked_remote_branch` kind, so we skip them here to avoid duplicate
    findings for the same underlying state.
    """
    findings: list[Finding] = []
    current = _current_branch(repo=repo)
    for branch in _list_local_branches(repo=repo):
        if _upstream(branch, repo=repo) is None:
            continue
        if not _origin_ref_exists(branch, repo=repo):
            continue
        relation, ahead, behind = _origin_relation(branch, repo=repo)
        if relation != "behind":
            continue
        is_current = branch == current
        findings.append(
            Finding(
                kind="branch_behind_origin",
                severity="warn",
                detail={
                    "branch": branch,
                    "behind_count": behind,
                    "is_current": is_current,
                },
                suggested_action=(
                    "current branch behind origin；不能用 git branch -f，詢問 pull / reset / skip"
                    if is_current
                    else f"git branch -f {branch} origin/{branch}"
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def _check_missed_runs(today: str | None = None, repo: Path = REPO_ROOT) -> list[Finding]:
    """Detect missed observer / reflector runs.

    Checks **yesterday** (not today): today's cron may not have fired yet
    when state_audit runs at 18:30 (observer fires at 20:00), so a missing
    today entry is a false alarm. Yesterday's miss is past tense — a clean
    judgment.

    Reflector is weekly; we treat it as missed when last_finished_at is
    older than REFLECTOR_STALENESS_DAYS.
    """
    today_str = today or datetime.now().strftime("%Y-%m-%d")
    today_date = date.fromisoformat(today_str)
    yesterday = (today_date - timedelta(days=1)).isoformat()
    findings: list[Finding] = []

    # Observer: yesterday's run log must exist
    observer_log = repo / "raw_signals" / yesterday / "observer_run.json"
    if not observer_log.exists():
        findings.append(
            Finding(
                kind="missed_observer_run",
                severity="warn",
                detail={"expected_date": yesterday},
                suggested_action=(
                    f"執行 python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe {yesterday}"
                ),
            )
        )

    # Reflector: check system_state.last_finished_at against staleness threshold.
    # Read system_state.json directly (plain JSON; keeps state_audit's no-LLM /
    # minimal-deps invariant intact — no infra.state import needed).
    roles = _read_state_roles(repo)
    reflector_state = roles.get("reflector") if roles else None
    last_finished = reflector_state.get("last_finished_at") if reflector_state else None

    suggested = "執行 python infra/periodic_jobs/ai_heartbeat/src/v0/reflector.py"
    if last_finished is None:
        # Never recorded a reflector run. Only flag when observer has run at
        # least once — otherwise fresh installs would always alarm.
        observer_state = roles.get("observer") if roles else None
        if observer_state and observer_state.get("last_finished_at"):
            findings.append(
                Finding(
                    kind="missed_reflector_run",
                    severity="warn",
                    detail={"last_finished_at": None},
                    suggested_action=suggested,
                )
            )
    else:
        try:
            last_dt = datetime.fromisoformat(last_finished)
            now_dt = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
            if (now_dt - last_dt) > timedelta(days=REFLECTOR_STALENESS_DAYS):
                findings.append(
                    Finding(
                        kind="missed_reflector_run",
                        severity="warn",
                        detail={"last_finished_at": last_finished},
                        suggested_action=suggested,
                    )
                )
        except ValueError:
            pass

    return findings


def _check_role_failed_runs(repo: Path = REPO_ROOT) -> list[Finding]:
    """Emit one Finding per role whose `last_status == "failed"` in
    `infra/state/system_state.json`.

    Roles missing `last_status` are skipped silently (defensive). Unknown roles
    fall back to a generic recovery hint that points the user at the role's
    run-log file.
    """
    findings: list[Finding] = []
    roles = _read_state_roles(repo=repo)
    if not roles:
        return findings

    for role_name, role_state in roles.items():
        if not isinstance(role_state, dict):
            continue
        if role_state.get("last_status") != "failed":
            continue

        hint = ROLE_RECOVERY_HINTS.get(
            role_name,
            _GENERIC_FAILED_HINT_TEMPLATE.format(role=role_name),
        )
        findings.append(
            Finding(
                kind="role_failed_run",
                severity="warn",
                detail={
                    "role": role_name,
                    "last_finished_at": role_state.get("last_finished_at"),
                    "last_target_date": role_state.get("last_target_date"),
                },
                suggested_action=hint,
            )
        )

    return findings


def _running_threshold_hours() -> float:
    """Resolve the stale-running threshold (env override or default).

    Read at audit time so env var changes are picked up without restart.
    Non-positive or unparseable values fall back to default with a warning.
    """
    raw = os.environ.get("STATE_AUDIT_RUNNING_THRESHOLD_HOURS")
    if raw is None:
        return RUNNING_THRESHOLD_HOURS
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "STATE_AUDIT_RUNNING_THRESHOLD_HOURS=%r is not a number; using default %.1f",
            raw,
            RUNNING_THRESHOLD_HOURS,
        )
        return RUNNING_THRESHOLD_HOURS
    if value <= 0:
        logger.warning(
            "STATE_AUDIT_RUNNING_THRESHOLD_HOURS=%r is non-positive; using default %.1f",
            raw,
            RUNNING_THRESHOLD_HOURS,
        )
        return RUNNING_THRESHOLD_HOURS
    return value


def _check_stale_running_role(repo: Path = REPO_ROOT) -> list[Finding]:
    """Emit one Finding per role whose `last_status == "running"` and
    `last_started_at` exceeds the threshold (default 2h, env-overridable).

    Pairs with the try/finally + atexit + SIGTERM hardening in role main()s:
    those handle controllable exits (clean exit, Python exception, SIGTERM),
    this audit catches the uncontrollable ones (SIGKILL, segfault, OOM,
    hardware loss). Without this check, a role killed mid-run leaves
    `last_status="running"` permanently and no failed-run finding ever fires.
    """
    findings: list[Finding] = []
    roles = _read_state_roles(repo=repo)
    if not roles:
        return findings

    threshold_hours = _running_threshold_hours()
    now_dt = datetime.now().astimezone()

    for role_name, role_state in roles.items():
        if not isinstance(role_state, dict):
            continue
        if role_state.get("last_status") != "running":
            continue

        last_started = role_state.get("last_started_at")
        if not isinstance(last_started, str):
            continue

        try:
            started_dt = datetime.fromisoformat(last_started)
        except ValueError:
            continue
        if started_dt.tzinfo is None:
            started_dt = started_dt.astimezone()

        elapsed_hours = (now_dt - started_dt).total_seconds() / 3600.0
        if elapsed_hours < threshold_hours:
            continue

        hint = ROLE_STALE_RUNNING_HINTS.get(
            role_name,
            _GENERIC_STALE_RUNNING_HINT_TEMPLATE.format(
                role=role_name,
                elapsed=elapsed_hours,
                threshold=threshold_hours,
            ),
        )
        findings.append(
            Finding(
                kind="stale_running_role",
                severity="warn",
                detail={
                    "role": role_name,
                    "last_started_at": last_started,
                    "last_target_date": role_state.get("last_target_date"),
                    "elapsed_hours": round(elapsed_hours, 2),
                    "threshold_hours": threshold_hours,
                },
                suggested_action=hint,
            )
        )

    return findings


def _read_state_roles(
    repo: Path = REPO_ROOT,
    ref: str | None = "origin/main",
) -> dict[str, Any]:
    """Read `roles` from system_state.json. Returns {} on any failure.

    By default reads from `origin/main` via `git show` to avoid cross-branch
    divergence: system_state.json is content-shaped (written on
    `content/<date>` branches, merged into main on a delay), so reading the
    working tree on a feature/* branch can yield stale state. The remote ref
    is the authoritative source.

    Pass `ref=None` to force reading the working tree (used by tests and
    explicit-override callers). Any failure on the git path (ref missing,
    timeout, malformed JSON) silently falls back to the working tree and
    emits a `logger.warning` for traceability — failures here SHALL NOT
    surface as audit `Finding`s.

    Caller MUST `git fetch` beforehand for `origin/main` to reflect the
    latest remote state.
    """
    if ref is not None:
        roles = _read_state_roles_from_ref(repo=repo, ref=ref)
        if roles is not None:
            return roles
    return _read_state_roles_from_working_tree(repo=repo)


def _read_state_roles_from_ref(repo: Path, ref: str) -> dict[str, Any] | None:
    """Try reading via `git show <ref>:infra/state/system_state.json`.

    Returns the parsed `roles` dict on success, or `None` to signal the
    caller should fall back. All failure modes log a warning.
    """
    rel_path = "infra/state/system_state.json"
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "git show %s:%s timed out; falling back to working tree",
            ref,
            rel_path,
        )
        return None
    except OSError as exc:
        logger.warning(
            "git show %s:%s failed (%s); falling back to working tree",
            ref,
            rel_path,
            exc,
        )
        return None

    if result.returncode != 0:
        logger.warning(
            "git show %s:%s exited %d (%s); falling back to working tree",
            ref,
            rel_path,
            result.returncode,
            (result.stderr or "").strip()[:200],
        )
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning(
            "git show %s:%s returned invalid JSON (%s); falling back to working tree",
            ref,
            rel_path,
            exc,
        )
        return None

    if not isinstance(data, dict):
        return {}
    roles = data.get("roles")
    return roles if isinstance(roles, dict) else {}


def _read_state_roles_from_working_tree(repo: Path) -> dict[str, Any]:
    """Read system_state.json from the working tree. Returns {} on any failure."""
    state_path = repo / "infra" / "state" / "system_state.json"
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    roles = data.get("roles")
    return roles if isinstance(roles, dict) else {}


def audit(repo: Path = REPO_ROOT, today: str | None = None) -> AuditReport:
    """Run all checks and return an AuditReport.

    Pure: never mutates working tree, never pushes/commits/checks-out.

    Caller MUST `git fetch` beforehand. Without a recent fetch, `origin/main`
    is stale and `_read_state_roles` may report old reflector state, leading
    to false `missed_reflector_run` findings. Both current callers comply:
    `cron.py` via `_fetch_all`, `/ctx:eod` via Step 1.
    """
    findings: list[Finding] = []
    findings.extend(_check_dirty_working_tree(repo=repo))
    findings.extend(_check_unmerged_content_branches(today=today, repo=repo))
    findings.extend(_check_stale_active_project_bridges(repo=repo))
    findings.extend(_check_unpushed_branches(repo=repo))
    findings.extend(_check_branch_behind_origin(repo=repo))
    findings.extend(_check_missed_runs(today=today, repo=repo))
    findings.extend(_check_role_failed_runs(repo=repo))
    findings.extend(_check_stale_running_role(repo=repo))

    return AuditReport(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        branch=_current_branch(repo=repo),
        findings=findings,
    )
