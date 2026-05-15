"""infra.state.lib — system_state.json 與 run log 的共用 helper.

設計參考：openspec/changes/add-system-state-coordination/design.md
Schema 說明：infra/state/README.md
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("infra.state")

REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_STATE_PATH = REPO_ROOT / "infra" / "state" / "system_state.json"
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"

SYSTEM_STATE_VERSION = 1

KNOWN_STATUSES = {"running", "ok", "failed"}


class StateError(Exception):
    """Raised when state file is malformed in an unrecoverable way.

    Callers should catch this and fall back to heuristic strategies, NOT
    propagate it as a hard error — state-related failures must never abort
    the consumer's main flow.
    """


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write `payload` as UTF-8 JSON to `path` atomically.

    Uses temp-file + `os.replace` so that interrupted writes never leave
    `path` in a partial state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# system_state.json
# ---------------------------------------------------------------------------


def read_system_state() -> dict[str, Any] | None:
    """Read system_state.json.

    Returns the parsed dict on success. Returns None when the file is
    missing, malformed, or has an unknown schema version — the caller
    SHALL fall back to its heuristic strategy. Logs a hint for missing /
    malformed cases so operators can spot the degradation.
    """
    if not SYSTEM_STATE_PATH.exists():
        logger.info(
            "system_state.json missing at %s — consumer SHALL fall back",
            SYSTEM_STATE_PATH,
        )
        return None
    try:
        data = json.loads(SYSTEM_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(
            "system_state.json malformed (%s) — consumer SHALL fall back", e
        )
        return None
    if not isinstance(data, dict):
        logger.warning(
            "system_state.json root is not an object — consumer SHALL fall back"
        )
        return None
    version = data.get("version")
    if version != SYSTEM_STATE_VERSION:
        logger.warning(
            "system_state.json version=%r unknown (expected %d) — fall back",
            version,
            SYSTEM_STATE_VERSION,
        )
        return None
    if not isinstance(data.get("roles"), dict):
        logger.warning(
            "system_state.json missing or malformed `roles` — fall back"
        )
        return None
    return data


def role_last_run(role: str) -> dict[str, Any] | None:
    """Return the per-role state dict, or None when state is unavailable.

    Convenience wrapper over `read_system_state()` for callers that only
    care about a single role.
    """
    state = read_system_state()
    if state is None:
        return None
    role_state = state["roles"].get(role)
    if not isinstance(role_state, dict):
        return None
    return role_state


def update_role_state(role: str, **fields: Any) -> None:
    """Merge `fields` into `roles.<role>` of system_state.json (atomic).

    Creates the file with default scaffold when missing. Unknown fields
    are written as-is — the schema is intentionally open for future
    extension. Status validation is performed when `last_status` is
    present.
    """
    if "last_status" in fields and fields["last_status"] not in KNOWN_STATUSES:
        raise StateError(
            f"Unknown last_status={fields['last_status']!r}; "
            f"expected one of {sorted(KNOWN_STATUSES)}"
        )

    state = read_system_state()
    if state is None:
        # Scaffold from scratch — a malformed file gets overwritten so that
        # later writes don't keep tripping the version/parse check.
        state = {"version": SYSTEM_STATE_VERSION, "roles": {}}

    role_state = state["roles"].get(role)
    if not isinstance(role_state, dict):
        role_state = {}
    role_state.update(fields)
    state["roles"][role] = role_state

    _atomic_write_json(SYSTEM_STATE_PATH, state)


# ---------------------------------------------------------------------------
# Run log: raw_signals/<date>/<role>_run.json
# ---------------------------------------------------------------------------


def _run_log_path(role: str, target_date: str) -> Path:
    return RAW_SIGNALS_DIR / target_date / f"{role}_run.json"


def write_run_log(
    role: str,
    target_date: str,
    started_at: str,
    finished_at: str | None,
    status: str,
    **extra: Any,
) -> Path:
    """Write `raw_signals/<target_date>/<role>_run.json` (atomic).

    Returns the path written. `extra` is merged into the payload — use it
    for `session_id`, `error_summary`, etc.
    """
    if status not in KNOWN_STATUSES:
        raise StateError(
            f"Unknown status={status!r}; expected one of {sorted(KNOWN_STATUSES)}"
        )

    payload: dict[str, Any] = {
        "kind": f"{role}_run",
        "role": role,
        "started_at": started_at,
        "finished_at": finished_at,
        "target_date": target_date,
        "status": status,
    }
    payload.update(extra)

    path = _run_log_path(role, target_date)
    _atomic_write_json(path, payload)
    return path
