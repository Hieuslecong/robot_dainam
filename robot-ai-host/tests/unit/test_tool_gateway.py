"""Typed Tool Gateway tests (spec 11, 19.3) — envelope, permission, audit."""

import asyncio
import json

import pytest
from pydantic import BaseModel

from app.tools.gateway import ToolGateway, ToolSpec


class EchoInput(BaseModel):
    value: str


@pytest.fixture
def gateway(tmp_path):
    return ToolGateway(audit_path=tmp_path / "audit.jsonl")


def _register(gateway, handler, **kwargs):
    gateway.register(ToolSpec(name="echo", input_model=EchoInput, handler=handler, **kwargs))


def test_success_envelope(gateway):
    async def handler(args):
        return {"echoed": args.value}

    _register(gateway, handler)
    result = asyncio.run(gateway.execute("echo", {"value": "hi"}, session_id="s1"))
    assert result.status == "success"
    assert result.data == {"echoed": "hi"}
    assert result.tool_call_id and result.timestamp


def test_unknown_tool_fails(gateway):
    result = asyncio.run(gateway.execute("nope", {}))
    assert result.status == "failed"
    assert result.error_code == "unknown_tool"


def test_invalid_input_rejected(gateway):
    async def handler(args):
        return {}

    _register(gateway, handler)
    result = asyncio.run(gateway.execute("echo", {"wrong": 1}))
    assert result.status == "failed"
    assert result.error_code == "invalid_input"


def test_confirmation_required_denied_without_confirm(gateway):
    executed = []

    async def handler(args):
        executed.append(True)
        return {}

    _register(gateway, handler, confirmation_required=True)
    result = asyncio.run(gateway.execute("echo", {"value": "x"}))
    assert result.status == "denied"
    assert result.error_code == "confirmation_required"
    assert executed == []  # zero unauthorized execution

    confirmed = asyncio.run(gateway.execute("echo", {"value": "x"}, confirmed=True))
    assert confirmed.status == "success"
    assert executed == [True]


def test_permission_enforced_outside_llm(gateway):
    async def handler(args):
        return {}

    _register(gateway, handler, permission="authenticated")
    result = asyncio.run(gateway.execute("echo", {"value": "x"}, user_id=""))
    assert result.status == "denied"
    assert result.error_code == "unauthenticated"


def test_handler_failure_never_reports_success(gateway):
    async def handler(args):
        raise RuntimeError("backend down")

    _register(gateway, handler)
    result = asyncio.run(gateway.execute("echo", {"value": "x"}))
    assert result.status == "failed"


def test_timeout_status(gateway):
    async def handler(args):
        await asyncio.sleep(1.0)
        return {}

    gateway.register(ToolSpec(name="echo", input_model=EchoInput, handler=handler, timeout_s=0.05))
    result = asyncio.run(gateway.execute("echo", {"value": "x"}))
    assert result.status == "timeout"


def test_audit_record_written(gateway):
    async def handler(args):
        return {"ok": 1}

    _register(gateway, handler)
    asyncio.run(gateway.execute("echo", {"value": "x"}, session_id="s9", user_id="u1"))
    lines = gateway.audit_path.read_text().strip().splitlines()
    record = json.loads(lines[-1])
    for key in ("tool_call_id", "user_id", "session_id", "normalized_input",
                "confirmation", "tool_result", "timestamp"):
        assert key in record
    assert record["session_id"] == "s9"
