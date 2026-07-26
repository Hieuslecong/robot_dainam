"""Action/personal tools tests (spec 11.1 MVP scope, Phase 3 gate)."""

import asyncio

import pytest

from app.tools import personal_tools
from app.tools.gateway import ToolGateway
from app.tools.personal_tools import register_personal_tools


@pytest.fixture
def gateway(tmp_path, monkeypatch):
    monkeypatch.setattr(personal_tools, "DB_PATH", tmp_path / "personal.db")
    gw = ToolGateway(audit_path=tmp_path / "audit.jsonl")
    register_personal_tools(gw)
    return gw


def test_create_reminder_real_backend_roundtrip(gateway):
    created = asyncio.run(gateway.execute(
        "create_reminder",
        {"user_id": "u1", "text": "Nộp học phí", "due_at": "2026-09-15T09:00:00"},
        user_id="u1",
    ))
    assert created.status == "success"
    listed = asyncio.run(gateway.execute("list_reminders", {"user_id": "u1"}, user_id="u1"))
    assert listed.data["reminders"][0]["text"] == "Nộp học phí"


def test_reminder_requires_authenticated_user(gateway):
    result = asyncio.run(gateway.execute(
        "create_reminder", {"user_id": "u1", "text": "x"}, user_id=""
    ))
    assert result.status == "denied"


def test_reminders_isolated_per_user(gateway):
    asyncio.run(gateway.execute(
        "create_reminder", {"user_id": "alice", "text": "A"}, user_id="alice"
    ))
    listed = asyncio.run(gateway.execute("list_reminders", {"user_id": "bob"}, user_id="bob"))
    assert listed.data["reminders"] == []


def test_draft_email_composes_but_never_sends(gateway):
    result = asyncio.run(gateway.execute(
        "draft_email",
        {"to": "daotao@example.edu.vn", "subject": "Hỏi lịch", "body_points": ["Hỏi về lịch thi"]},
    ))
    assert result.status == "success"
    assert result.data["draft"]["subject"] == "Hỏi lịch"
    assert "CHƯA được gửi" in result.message


def test_send_email_interface_only_denied_then_fails(gateway):
    # Without confirmation: denied — zero unauthorized action.
    denied = asyncio.run(gateway.execute(
        "send_email",
        {"user_id": "u1", "to": "a@b.vn", "subject": "s", "body": "b"},
        user_id="u1",
    ))
    assert denied.status == "denied"
    # With confirmation: still fails (no real backend) — zero false success.
    confirmed = asyncio.run(gateway.execute(
        "send_email",
        {"user_id": "u1", "to": "a@b.vn", "subject": "s", "body": "b"},
        user_id="u1",
        confirmed=True,
    ))
    assert confirmed.status == "failed"
    assert "interface-only" in confirmed.message


def test_interface_only_tools_marked(gateway):
    for name in ("create_calendar_event", "send_email", "create_support_ticket"):
        assert gateway.get(name).interface_only is True
        assert gateway.get(name).confirmation_required is True
