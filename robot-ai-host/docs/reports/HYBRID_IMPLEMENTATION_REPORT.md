# Hybrid Implementation Report

## Final status

**PARTIAL — source implementation complete; live model/microphone acceptance not run in this restricted environment.**

## Implemented

- Added `hybrid_local_vi` profile.
- Added local Whisper backend selection:
  - MLX Whisper on Apple Silicon.
  - Faster-Whisper on Linux/CPU/NVIDIA.
- Added Piper HTTP TTS with sentence aggregation.
- Added generic OpenAI-compatible LLM settings:
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_DEFAULT_HEADERS_JSON`
  - timeout/retry settings.
- Retained legacy `OPENAI_API_KEY` and `OPENAI_MODEL` fallbacks.
- Added per-session Piper HTTP client lifecycle and cleanup.
- Added conservative `LOCAL_STT_MAX_SESSIONS=1` gate.
- Added macOS/Linux installers, Piper launcher and Hybrid host launcher.
- Added Linux Hybrid Dockerfiles and Compose file.
- Added Hybrid profile validation script.
- Added documentation and tests.

## Tests run

```text
Python: 84 passed, 1 skipped
Frontend source contract: 4 passed
Vendored Pipecat v1.6.0 API contract: PASS
Python compileall: PASS
```

The skipped Python test is the runtime import test because the restricted environment does not have the optional Pipecat runtime installed.

## Not run

- `npm ci` / Vite production build: no package-registry DNS.
- Optional Whisper/MLX packages: no package-registry DNS.
- Piper 1.5.0/model download: no package-registry/model-network access.
- Docker: Docker engine unavailable.
- Physical microphone/speaker test.
- Live LLM endpoint inference.
- Latency and barge-in acceptance on target hardware.

## LLM endpoint changes

The user can switch provider without source changes:

```env
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=provider-token
LLM_MODEL=provider-model-id
```

The token remains server-side and is not sent to the browser.
