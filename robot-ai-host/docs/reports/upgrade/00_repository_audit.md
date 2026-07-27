# 00 — Repository Audit (Phase 0 entry)

Date: 2026-07-26
Environment: see `artifacts/upgrade/environment.txt` (macOS 15.7.5, arm64 M1, Python 3.14.3 system / 3.12 in venvs, node v22.23.1, npm 10.9.8, uv 0.9.27)

## Tooling reality

- `pyproject.toml` + `uv.lock` present → canonical runner: `uv run pytest -q` (Python 3.11–3.12 required; venvs are 3.12).
- `.venv-hybrid` and `.venv-piper` exist (uv-managed cpython 3.12). Piper runs from `.venv-piper` via `scripts/run_piper.sh`.
- **Not a git repository.** User declined git init. Backup: `../artifacts/pre-upgrade-snapshot/` (rsync, excl. venvs/models/node_modules).
- Frontend: Vite + `@pipecat-ai/client-js` 1.12.0 + `@pipecat-ai/small-webrtc-transport` 1.10.5, tests via `node --test`.

## Config duplication (confirmed)

| Path | Content | Loaded by |
|---|---|---|
| `configs/profiles.yaml` | runtime profiles (mock, google_vi, hybrid_local_vi) | `app/config.py:17` `PROFILES_PATH` |
| `config/assistant_school.yaml` | persona/assistant profile | `app/core/system_prompt.py:10` + `Settings.assistant_profile` default `config/assistant_school.yaml` |

Two directories, both active, different loaders. No silent fallback between them today, but ambiguity is real. Decision (design doc): consolidate to `config/`.

## Active profile

`DEFAULT_PROFILE=mock` in `.env.example`; real local profile is `hybrid_local_vi` (whisper_local + openai_compatible + piper_http).

## Builders

- STT: `app/pipecat_runtime/pipeline_factory.py` — `_create_local_whisper_stt` (MLX `whisper-large-v3-turbo-q4` on Apple Silicon, faster-whisper elsewhere), GoogleSTT for google_vi, MockSTT for mock.
- LLM: `_create_openai_compatible_llm` — OpenAILLMService, endpoint/token/model/headers all from env (`LLM_*` with legacy `OPENAI_*` fallback). System prompt injected as `system_instruction`. Temperature/max_tokens single global (0.2 / 160).
- TTS: PiperHttpTTSService (sentence aggregation, `VietnameseSpeechTextFilter`), GoogleTTS, MockTTS.
- Per-profile pipelines hard-coded by name in `create_pipeline` (mock / google_vi / hybrid_local_vi).

## Session lifecycle

`app/sessions.py` SessionManager: create/heartbeat/activate/error/close/cleanup_expired/validate_ownership/register_worker. JWT auth (`app/auth.py`). Worker per session (`worker_factory.py`) with connect/disconnect handlers.

## Context aggregation

`LLMContext` + `LLMContextAggregatorPair` per pipeline. System prompt added only in mock path via `context.add_message`; google/hybrid rely on `system_instruction`. **No turn limit, no summarization, no reset endpoint, unbounded growth risk** (Settings has `conversation_max_turns: 10` but nothing enforces it in pipeline).

## VAD / Smart Turn

SileroVADAnalyzer in aggregators (`_build_aggregators`). `TurnProfile.smart_turn` flag exists, `false` in all profiles; no Smart Turn wiring found.

## Processors

- `STTGuard` (app/processors/stt_guard.py)
- `StreamDeduplicator`
- `ResponsePolicyProcessor` (max sentences/words — hard length policy already processor-side)
- `VietnameseSpeechTextFilter`, `text_sanitizer`

## Metrics

`LatencyTracker` (JSONL + p50/p90/p95/max) with 14 metric names; `RuntimeMetricsObserver` bridges Pipecat metrics. **Gap vs spec 17.1 (16-event timeline):** missing explicit `physical_speech_start/end`, `vad_speech_start/end`, `turn_finalized`, `llm_request_start`, `first_speakable_chunk`, `tts_request_start`, `server_audio_sent`, `client_audio_received`, `interruption_detected`, `client_audio_stopped` as unified timeline events; present as derived durations only (turn_end_to_stt_final, llm_first_token, tts_first_audio, client_audible_start, barge_in_audible_stop...). No `router_latency` / `router_bypass_rate` yet (Phase 3).

## Browser capture

`clients/browser/src/main.ts` enables `audio_input: true` via Pipecat client; **no explicit `echoCancellation`/`noiseSuppression`/`autoGainControl` constraints and no UI/log exposure** → Phase 0.6 work.

## Function calling / agent

None. No tools, no router, no flows, no task state. `app/robot/` has messages/validator/fake_adapter (behavior validation exists). `app/storage/`, `app/api/`, `app/voice/` empty dirs.

## Memory

None beyond in-process LLMContext. No long-term store.

## Knowledge

`knowledge/README.md` placeholder only.

## Models on disk

`models/piper/` only (Piper voice). Whisper MLX models pulled via HF cache at runtime.

## License inventory (initial, unverified items marked)

- pipecat-ai 1.6.0 — BSD-2-Clause (verify at lock report)
- fastapi/uvicorn/pydantic/structlog/httpx/pyyaml/PyJWT — permissive (verify)
- Piper (rhasspy) — MIT; voice `vi_VN-vais1000-medium` license **NOT VERIFIED**
- whisper-large-v3-turbo (MLX community) — Apache-2.0 base, conversion license **NOT VERIFIED**
- @pipecat-ai JS clients — BSD-2-Clause (verify)

## Prior reports

Top-level FINAL_STATUS.md, KNOWN_LIMITATIONS.md, etc. from previous implementation round remain; upgrade-round reports live in `reports/upgrade/` and will supersede.

## Phase 0 work list derived

1. Config → `config/` single source (+test, remove `configs/`).
2. DEPENDENCY_LOCK_REPORT / MODEL_INVENTORY / LICENSE_INVENTORY.
3. Persona per spec 9.4–9.5, `PERSONA_NAME` env, remove admin boilerplate, unify system-prompt injection.
4. Context: enforce recent-turn cap + summarization + reset + disconnect cleanup.
5. Metrics: unified 16-event timeline emission.
6. Browser: explicit AEC/NS/AGC constraints + exposure.
7. Tests + `reports/upgrade/01_foundation_cleanup.md` + HUMAN_TASK_CHECKLIST.md.
