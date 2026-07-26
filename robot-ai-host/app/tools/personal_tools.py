"""Personal + action tools (spec 11.1, MVP scope per v1.1).

Real local backends (count toward acceptance):
- create_note, create_reminder, list_reminders — SQLite, verifiable.
- draft_email — compose only, never sends.

Interface-only (fake adapter, NOT acceptance evidence — spec 11.1):
- create_calendar_event, send_email, create_support_ticket.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from app.tools.gateway import ToolGateway, ToolSpec

DB_PATH = Path("artifacts/personal.db")


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reminders ("
        "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, text TEXT NOT NULL, "
        "due_at TEXT, created_at TEXT NOT NULL, done INTEGER DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, text TEXT NOT NULL, "
        "created_at TEXT NOT NULL)"
    )
    return conn


# --- Real backends ------------------------------------------------------------


class ReminderInput(BaseModel):
    user_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=500)
    due_at: str | None = None  # ISO-8601; normalized upstream


async def create_reminder(args: ReminderInput) -> dict:
    reminder_id = uuid.uuid4().hex[:12]
    with _db() as conn:
        conn.execute(
            "INSERT INTO reminders (id, user_id, text, due_at, created_at) VALUES (?,?,?,?,?)",
            (reminder_id, args.user_id, args.text, args.due_at,
             time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
    # Read back — success is claimed only for a verifiably persisted row.
    with _db() as conn:
        row = conn.execute("SELECT id FROM reminders WHERE id=?", (reminder_id,)).fetchone()
    if row is None:
        return {"_status": "failed", "_message": "Không lưu được nhắc nhở."}
    return {"reminder_id": reminder_id, "_message": "Đã tạo nhắc nhở."}


class ListRemindersInput(BaseModel):
    user_id: str = Field(min_length=1)


async def list_reminders(args: ListRemindersInput) -> dict:
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, text, due_at, done FROM reminders WHERE user_id=? ORDER BY created_at",
            (args.user_id,),
        ).fetchall()
    return {"reminders": [
        {"id": r[0], "text": r[1], "due_at": r[2], "done": bool(r[3])} for r in rows
    ]}


class NoteInput(BaseModel):
    user_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)


async def create_note(args: NoteInput) -> dict:
    note_id = uuid.uuid4().hex[:12]
    with _db() as conn:
        conn.execute(
            "INSERT INTO notes (id, user_id, text, created_at) VALUES (?,?,?,?)",
            (note_id, args.user_id, args.text, time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
    return {"note_id": note_id, "_message": "Đã lưu ghi chú."}


class DraftEmailInput(BaseModel):
    to: str = Field(min_length=3, max_length=200)
    subject: str = Field(min_length=1, max_length=200)
    body_points: list[str] = Field(min_length=1, max_length=10)


async def draft_email(args: DraftEmailInput) -> dict:
    """Compose only (spec 11.1) — the draft is returned, never transmitted."""
    body = "\n".join(f"- {point}" for point in args.body_points)
    draft = (
        f"Kính gửi {args.to},\n\n{body}\n\nTrân trọng."
    )
    return {"draft": {"to": args.to, "subject": args.subject, "body": draft},
            "_message": "Đã soạn nháp email. Email CHƯA được gửi."}


# --- Interface-only fakes (contract tests only; not acceptance evidence) ------


class CalendarEventInput(BaseModel):
    user_id: str
    title: str = Field(min_length=1, max_length=200)
    start_at: str
    end_at: str | None = None


async def create_calendar_event(args: CalendarEventInput) -> dict:
    return {"_status": "failed", "_message": (
        "Chưa có backend lịch của trường — tool này là interface-only trong MVP."
    )}


class SendEmailInput(BaseModel):
    user_id: str
    to: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject: str
    body: str


async def send_email(args: SendEmailInput) -> dict:
    return {"_status": "failed", "_message": (
        "Chưa có backend email của trường — tool này là interface-only trong MVP."
    )}


class SupportTicketInput(BaseModel):
    user_id: str
    summary: str = Field(min_length=5, max_length=500)


async def create_support_ticket(args: SupportTicketInput) -> dict:
    return {"_status": "failed", "_message": (
        "Chưa có backend ticket của trường — tool này là interface-only trong MVP."
    )}


def register_personal_tools(gateway: ToolGateway) -> None:
    gateway.register(ToolSpec(
        name="create_reminder", input_model=ReminderInput, handler=create_reminder,
        permission="authenticated", confirmation_required=False, timeout_s=5.0,
    ))
    gateway.register(ToolSpec(
        name="list_reminders", input_model=ListRemindersInput, handler=list_reminders,
        permission="authenticated", timeout_s=5.0,
    ))
    gateway.register(ToolSpec(
        name="create_note", input_model=NoteInput, handler=create_note,
        permission="authenticated", timeout_s=5.0,
    ))
    gateway.register(ToolSpec(
        name="draft_email", input_model=DraftEmailInput, handler=draft_email,
        timeout_s=5.0,
    ))
    # Confirmed writes (spec 10.6) — and interface-only in MVP (spec 11.1).
    gateway.register(ToolSpec(
        name="create_calendar_event", input_model=CalendarEventInput,
        handler=create_calendar_event, permission="authenticated",
        confirmation_required=True, interface_only=True,
    ))
    gateway.register(ToolSpec(
        name="send_email", input_model=SendEmailInput, handler=send_email,
        permission="authenticated", confirmation_required=True, interface_only=True,
    ))
    gateway.register(ToolSpec(
        name="create_support_ticket", input_model=SupportTicketInput,
        handler=create_support_ticket, permission="authenticated",
        confirmation_required=True, interface_only=True,
    ))
