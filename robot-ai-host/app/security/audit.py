"""Structured audit logging for security-relevant operations.

Logs: principal, action, target, timestamp, result, source_ip, request_id.
Never logs: tokens, API keys, secrets, PII content.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Any

from app.logging_utils import get_logger

logger = get_logger("audit")

# Context-local request ID for tracing through async handlers
_request_id: ContextVar[str] = ContextVar("audit_request_id", default="")


def set_request_id(request_id: str | None = None) -> str:
    rid = request_id or uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id.get() or "-"


class AuditLogger:
    """Structured audit logger for security events."""

    @staticmethod
    def log(
        action: str,
        *,
        principal: str = "anonymous",
        target: str = "",
        result: str = "success",
        source_ip: str = "-",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event. NEVER include tokens, API keys, or secrets."""
        entry = {
            "principal": principal,
            "action": action,
            "target": target,
            "result": result,
            "source_ip": source_ip,
            "request_id": get_request_id(),
            "timestamp": time.time(),
        }
        if extra:
            # Sanitize: never log keys named "token", "secret", "api_key", "password"
            safe = {k: v for k, v in extra.items() if not any(s in k.lower() for s in ("token", "secret", "api_key", "password", "key"))}
            entry.update(safe)

        logger.info("audit", **entry)


# Singleton
audit_log = AuditLogger()
