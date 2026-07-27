# 04 — Phase 3: Action Agent (v1.1 reduced scope, spec 11.1)

Date: 2026-07-26
Status: **PASS (code + tests)** on the real-backend tools; interface-only tools explicitly excluded from acceptance per spec.

## Real backends (count toward the gate)

- `create_reminder` — SQLite (`artifacts/personal.db`), success only after read-back verification of the persisted row. `list_reminders` proves round-trip; per-user isolation tested.
- `create_note` — same backend.
- `draft_email` — composes and returns the draft; **never sends**; message states "Email CHƯA được gửi".

## Confirmation + permission (spec 10.6, 11.4) — [app/tools/gateway.py](../../app/tools/gateway.py)

- Enforced in the gateway, OUTSIDE the LLM: `confirmation_required` tools return `denied` without the orchestrator's `confirmed=True`; handler never runs (tested: zero unauthorized execution).
- `authenticated` permission denies empty user identity.
- Input validated post-extraction (pydantic); handler exception/timeout can never surface as success (tested: zero false success).

## Audit (spec 19.3)

JSONL at `artifacts/tool-audit.jsonl`: tool_call_id, user_id, session_id,
normalized input, confirmation, tool result, timestamp, error. Written for every
call including denials (tested).

## Interface-only (NOT acceptance evidence — spec 11.1)

`create_calendar_event`, `send_email`, `create_support_ticket`: registered with
`interface_only=True` + `confirmation_required=True`; handlers return `failed`
with an explicit "no school backend" message. Contract tests only. They move to
real backends when the school provides them (MVP+1).

## Tests

`test_tool_gateway.py` (8), `test_personal_tools.py` (6) — in the 171-test suite.

## Gate (spec §22 Phase 3)

| Item | Status |
|---|---|
| Zero unauthorized action (real-backend tools) | PASS (gateway-enforced, tested) |
| Zero false success (real-backend tools) | PASS (read-back verify + envelope, tested) |
| Confirmation / ACK / audit | PASS |
| Calendar/send_email/ticket | interface-only by design — excluded from gate |

End-to-end (voice → router → flow → confirm → tool) needs a live session — part of the human soak checklist.
