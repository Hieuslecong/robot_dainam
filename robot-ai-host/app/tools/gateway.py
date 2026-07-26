"""Typed Tool Gateway (spec 11) — contracts, envelope, permission, audit.

Rules enforced HERE, outside the LLM (spec 11.4 / 19.4):
- input validated against the tool's schema after extraction;
- confirmation-required tools never execute without an explicit confirmed flag
  from the orchestrator (never from retrieved text);
- every call is audited (spec 19.3);
- success is only reported when the handler returns success (spec 10.7).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.logging_utils import get_logger

logger = get_logger(__name__)

AUDIT_PATH = Path("artifacts/tool-audit.jsonl")


class ToolResult(BaseModel):
    """Result envelope (spec 11.3)."""

    tool_call_id: str
    tool_name: str
    status: str  # success|partial|failed|timeout|denied
    data: dict = {}
    message: str = ""
    error_code: str | None = None
    retryable: bool = False
    timestamp: str = ""


@dataclass
class ToolSpec:
    name: str
    input_model: type[BaseModel]
    handler: Callable[[BaseModel], Awaitable[dict]]
    permission: str = "public"  # public|authenticated
    confirmation_required: bool = False
    timeout_s: float = 10.0
    retryable: bool = False
    interface_only: bool = False  # spec 11.1: fake adapter, NOT acceptance evidence


@dataclass
class ToolGateway:
    audit_path: Path = AUDIT_PATH
    _tools: dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    async def execute(
        self,
        name: str,
        arguments: dict,
        *,
        session_id: str = "",
        user_id: str = "",
        confirmed: bool = False,
    ) -> ToolResult:
        call_id = uuid.uuid4().hex
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        def envelope(status: str, **kwargs) -> ToolResult:
            result = ToolResult(
                tool_call_id=call_id,
                tool_name=name,
                status=status,
                timestamp=stamp,
                **kwargs,
            )
            self._audit(result, session_id=session_id, user_id=user_id,
                        arguments=arguments, confirmed=confirmed)
            return result

        spec = self._tools.get(name)
        if spec is None:
            return envelope("failed", error_code="unknown_tool",
                            message=f"Tool không tồn tại: {name}")

        # Permission enforced outside the LLM (spec 11.4).
        if spec.permission == "authenticated" and not user_id:
            return envelope("denied", error_code="unauthenticated",
                            message="Cần xác thực người dùng trước khi thực hiện.")

        # Confirmation gate (spec 10.6): only the orchestrator sets confirmed.
        if spec.confirmation_required and not confirmed:
            return envelope("denied", error_code="confirmation_required",
                            message="Hành động này cần bạn xác nhận trước.")

        try:
            validated = spec.input_model.model_validate(arguments)
        except Exception as exc:
            return envelope("failed", error_code="invalid_input", message=str(exc)[:200])

        try:
            data = await asyncio.wait_for(spec.handler(validated), timeout=spec.timeout_s)
        except asyncio.TimeoutError:
            return envelope("timeout", error_code="timeout", retryable=spec.retryable,
                            message="Tool không phản hồi kịp thời.")
        except Exception as exc:
            logger.warning("tool_failed", tool=name, error=str(exc))
            return envelope("failed", error_code="tool_error", retryable=spec.retryable,
                            message="Tool gặp lỗi khi thực hiện.")

        status = data.pop("_status", "success")
        message = data.pop("_message", "")
        return envelope(status, data=data, message=message)

    def _audit(self, result: ToolResult, *, session_id: str, user_id: str,
               arguments: dict, confirmed: bool) -> None:
        """Append the spec 19.3 audit record. Never raises."""
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "tool_call_id": result.tool_call_id,
                "user_id": user_id,
                "session_id": session_id,
                "normalized_input": arguments,
                "confirmation": confirmed,
                "tool_result": {"status": result.status, "error_code": result.error_code},
                "timestamp": result.timestamp,
                "error": result.error_code,
            }
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("tool_audit_write_failed", error=str(exc))
