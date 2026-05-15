"""state_audit — 純規則性狀態審計角色。

與 `ai_heartbeat` 平行存在，無 LLM 或外部 API 依賴：僅依賴 Python 標準庫
與 `git` CLI。對外暴露 `core.audit() -> AuditReport`，給 `/ctx:eod`
與 `cron.py` 共用。
"""

from .core import AuditReport, Finding, audit

__all__ = ["AuditReport", "Finding", "audit"]
