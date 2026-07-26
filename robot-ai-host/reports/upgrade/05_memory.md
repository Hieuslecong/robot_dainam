# 05 — Phase 4: Memory

Date: 2026-07-26
Status: **PASS (code + tests)**

## Implementation

- [app/core/memory.py](../../app/core/memory.py): consent-gated preference store.
  - Allowlist (13.3): preferred_name, address_style, preferred_voice, accessibility, frequent_schedule.
  - Forbidden content (13.5) refused even WITH consent: passwords/API keys/tokens, medical, financial (pattern-based; patterns are a floor, not a ceiling — extend with real cases).
  - One JSON file per user id ⇒ cross-user leakage impossible by construction.
  - Disabling storage also clears existing items.
- API (13.4) in [app/main.py](../../app/main.py), device-JWT-authenticated:
  - `GET /v1/memory/{user_id}` — view
  - `POST /v1/memory/{user_id}` — store (requires `consent: true`)
  - `DELETE /v1/memory/{user_id}/{kind}` — delete one
  - `DELETE /v1/memory/{user_id}` — delete all
  - `POST /v1/memory/{user_id}/disable` — disable/enable
- Session memory (6–8 turns + summarization) was delivered in Phase 0 (`ContextManager`).

## Tests

`test_memory.py` (7): consent required, allowlist enforced, sensitive refusal,
delete one/all, disable semantics, **zero cross-user leakage**.

## Gate (spec §22 Phase 4)

| Item | Status |
|---|---|
| Recent context + summary | PASS (Phase 0) |
| Opt-in preference | PASS |
| Memory API | PASS (UI = settings page candidate, not built — API-first) |
| Delete/disable | PASS |
| Zero cross-user leakage | PASS (structural + tested) |

## Honest limitations

- Voice-flow integration ("nhớ tên mình nhé" → consent dialog → store) lands with the orchestrator LLM wiring; the store + API are ready.
- Forbidden-content regex is heuristic; legal/privacy review should extend it.
