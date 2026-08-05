# 01 — Phase 0 Foundation Cleanup

Date: 2026-07-26
Status: **PARTIAL** (code + tests complete; 30-min soak needs a human — see HUMAN_TASK_CHECKLIST.md)

## 4.1 Config — DONE

- `config/` is the single runtime source. `configs/profiles.yaml` → `config/profiles.yaml`; `configs/` deleted.
- `app/config.py`: `CONFIG_DIR`/`PROFILES_PATH` point at `config/`; a resurrected `configs/` now raises `RuntimeError` (no silent fallback).
- Dockerfiles updated (`COPY config ./config`). Side-effect bug fixed: images previously shipped without `config/assistant_school.yaml`, so Docker deployments silently ran the fallback persona.
- Tests: `test_config_single_source_of_truth`, `test_legacy_configs_dir_fails_loudly`.

## 4.2 Dependency — DONE

- `DEPENDENCY_LOCK_REPORT.md`, `MODEL_INVENTORY.md`, `LICENSE_INVENTORY.md` created.
- Honest gaps recorded: hybrid venv STT extras and Piper venv not lock-pinned yet (Phase 1/2 scope).

## 4.3 Persona — DONE

- `app/core/system_prompt.py` rewritten per spec 9.4–9.5: xưng hô mình–bạn, warm/calm/proactive, style rules, honesty/safety block. No administrative boilerplate.
- `PERSONA_NAME` env (Settings.persona_name) — name never hard-coded; "N.E.K.O" awaits school confirmation (checklist #2).
- `config/assistant_school.yaml` rewritten to match. Settings UI in `app/main.py` now renders the configured name.
- Hard length limits stay in `ResponsePolicyProcessor` (already processor-side); prompt gives soft per-intent length guidance only.
- Conversation temperature 0.2 → 0.5 (spec 9.6 conversation band).
- Tests: `tests/unit/test_system_prompt.py` (5 tests incl. no-hard-coded-name and token budget).

## 4.4 Context — DONE (deterministic summarizer; LLM summarizer deferred by design)

- `app/core/context_manager.py`: recent-turn cap (`CONVERSATION_MAX_TURNS`, default 8 per spec 13.1), rolling single summary message, never cuts an unfinished tool-call sequence, bounded summary size.
- `app/processors/context_compactor.py` wired into all three pipelines between user aggregator and LLM.
- Reset: RTVI client message `conversation.reset` → `PipelineBundle.reset_conversation()` (keeps system head only).
- Disconnect cleanup: pre-existing path verified (`on_client_disconnected` → runner.cancel → `close_session` → `bundle.aclose`).
- Summarization is deterministic compression (no extra LLM call). An LLM-written summary can replace `ContextManager._summarize` in Phase 3+ without touching callers. Task-state preservation beyond tool-sequence protection is N/A until task state exists (Phase 4).
- Tests: `tests/unit/test_context_manager.py` (7 tests).

## 4.5 Metrics — DONE (server-side events; client/physical events by transport/human)

- `LatencyTracker`: spec 17.1 canonical 16-event list, `turn_timeline` record (per-turn offsets), critical-path segment metrics (`stt_final_to_llm_first_token`, `llm_first_token_to_first_speakable_chunk`, `first_speakable_chunk_to_tts_first_audio`, `speech_end_to_server_audio_sent`), reserved `router_latency`/`router_bypass_rate` names (Phase 3).
- `RuntimeMetricsObserver` + `TurnTimeline`: marks vad start/end, turn_finalized (VAD stop — no Smart Turn yet), stt_final, llm_request_start, llm_first_token, first_speakable_chunk, tts_request_start, tts_first_audio, server_audio_sent, interruption_detected; client events (`client_audio_received`, `client_audible_start`, `client_audio_stopped`) arrive via RTVI messages.
- `physical_speech_start/end`: not producible without a reference microphone — measured only in human mic sessions; recorded as such, not faked.
- Summaries expose count/p50/p90/p95/max (existing). No target marked "đạt" — no runtime turns executed this session.
- Tests: `tests/unit/test_turn_timeline.py` (4 tests).

## 4.6 Browser capture — DONE

- `clients/browser/src/main.ts`: local audio track now gets explicit `applyConstraints({echoCancellation, noiseSuppression, autoGainControl: true})`, real values read from `track.getSettings()`, shown in mic status UI and sent to server as `client.capture.settings` (logged server-side as evidence).
- No duplicate server AEC built (per spec 8.5 — browser AEC must be tested first).
- Test: source-contract test added (frontend suite now 5 tests).

## 4.7 Tests — evidence

| Suite | Result | Evidence |
|---|---|---|
| Python (`.venv-hybrid/bin/python -m pytest tests/ -q`) | **108 passed** | `artifacts/upgrade/python-tests.txt` |
| Frontend (`npm run test --prefix clients/browser`) | **5 passed** | `artifacts/upgrade/frontend-tests.txt` |
| Frontend build | **OK** | `artifacts/upgrade/frontend-build.txt` |

Runner note: `uv run pytest` currently resolves to system Python 3.14 (missing deps) — canonical runner is `.venv-hybrid/bin/python -m pytest` (repo's real tooling, per prompt §3). `npm ci` was **skipped** (node_modules present and healthy; disk at ~850MB free makes reinstall risky) — run after disk cleanup.

## Gate status (Phase 0, spec §22)

| Gate item | Status |
|---|---|
| One config source, tests prove it | PASS |
| Dependencies pinned + reports | PASS (gaps recorded) |
| Persona per spec, configurable name | PASS |
| Context cap/summarization/reset/cleanup | PASS (code+tests) |
| Metrics timeline complete | PASS (server events; client/physical noted) |
| AEC/VAD evidence | PARTIAL — code done; live browser evidence needs human run |
| 30-min soak, no context growth, no stale audio | **BLOCKED — human task #1** |

**Phase 0 verdict: PARTIAL** — all machine-executable items complete with tests; soak + mic listening are human tasks.

## Environment risk

Disk: ~850MB free of 228GB. Phase 1 model downloads (several GB) are **BLOCKED** until cleanup (checklist #0).

## Next session

Read this report + design doc (`docs/superpowers/specs/2026-07-26-upgrade-plan-design.md`) → execute Phase 1 (STT profiles + round-1 public-corpus benchmark) after disk cleanup.
