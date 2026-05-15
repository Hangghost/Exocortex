"""infra.state — 系統執行狀態共用 helper。

提供 read_system_state / update_role_state / write_run_log 三個函式給
periodic jobs 與互動命令使用。詳見 README.md。
"""

from .lib import (
    SYSTEM_STATE_PATH,
    SYSTEM_STATE_VERSION,
    read_system_state,
    update_role_state,
    write_run_log,
    role_last_run,
    StateError,
)

__all__ = [
    "SYSTEM_STATE_PATH",
    "SYSTEM_STATE_VERSION",
    "read_system_state",
    "update_role_state",
    "write_run_log",
    "role_last_run",
    "StateError",
]
