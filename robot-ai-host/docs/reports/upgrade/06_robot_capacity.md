# 06 — Phase 5: Robot behavior, capacity, hardening

Date: 2026-07-26
Status: **PARTIAL** — machine-executable items done; capacity/soak need live runtime (human checklist).

## Robot behavior (spec 15.4)

- Expression Composer style → behavior mapping validated end-to-end against the
  robot validator allowlist (`test_expression.py::test_every_style_maps_to_validated_behavior`).
- Allowlist extended with the seven spec 15.4 behavior IDs; raw motor commands
  still rejected (`validate_raw_motor_check`, Phase-0 tests).
- Wake/idle gate (spec 8.7) delivered in Phase 1: idle drops transcriptions,
  timeout clears transient context, RTVI `robot.wake`/`robot.sleep`.

## Resource control (spec 18.3)

Already enforced and verified in code:
- `max_sessions` (server-wide, sessions.py).
- `local_stt_max_sessions` (hybrid STT concurrency cap).
- VieNeu expressive renders serialized (asyncio lock — max 1 concurrent CPU render).
- Disconnect cleanup path (Phase 0 verified); timeout/cancel via runner.

Not built (per spec 18.2: no shared-pool work without capacity evidence first):
shared STT/TTS pools — decision follows the 2-session benchmark.

## Capacity — BLOCKED (human)

- 1 full inference session, then 2 concurrent (18.1): needs live mic sessions → HUMAN_TASK_CHECKLIST.
- Four-session capacity: not claimed (spec §5.8).
- 30-min soak (23.4): HUMAN_TASK_CHECKLIST #1.

## Deployment hardening

- Dockerfiles ship `config/` (fixed Phase 0); `.env` gitignored; secrets never logged (Phase 0 verified).
- Piper stays as sidecar per license posture (spec 21).
