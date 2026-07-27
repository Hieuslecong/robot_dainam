# Implementation Audit

## Baseline received

Repository already contained FastAPI REST endpoints, an in-memory session manager, a raw browser WebRTC client, mock providers, Pipecat pipeline code, tests and Docker files. The critical voice data plane was not proven end-to-end.

## Confirmed baseline defects

| Finding | Severity | Resolution in this revision |
|---|---:|---|
| Mock STT returned fixed transcript list | High | Retained only as explicitly scripted test harness; docs/UI no longer claim ASR |
| Mock TTS inherited `AIService` and synthesized per token | Critical | Replaced by official `TTSService` with `TextAggregationMode.SENTENCE` |
| Cloud pipeline read secrets from `os.environ` | Critical | Provider factory receives typed `Settings` and validated profile |
| Google TTS had no required Vietnamese voice | Critical | `GOOGLE_TTS_VOICE` required, `vi-VN-` + Chirp3-HD/Journey validation |
| CLI profile could be overwritten | High | CLI now constructs a `Settings` override before `create_app()` |
| Browser used raw `RTCPeerConnection` | Critical | Replaced source with `PipecatClient` + official `SmallWebRTCTransport` |
| No proper RTVI client handshake | Critical | Official client SDK handles transport/RTVI ready lifecycle |
| No PATCH ICE endpoint | High | Added POST/PATCH SmallWebRTC signaling endpoints |
| Barge button only paused browser audio | Critical | Relabeled debug-only; acceptance requires microphone-driven Pipecat interruption |
| Runtime metrics tracker was disconnected | Critical | Added Pipecat observers, JSONL bridge, client audible/barge/connect metrics |
| Behavior code not connected | High | Sends validated `greet` on RTVI ready and records browser ACK latency |
| Worker runner used `auto_end=False` | Critical | Runner now uses default auto-end and session close cancels runner |
| Docker synced before source copy and ignored lock | High | Multi-stage frontend/Python image; `uv sync --frozen --no-dev` |
| ZIP reference verification required `.git` | Medium | Added `UPSTREAM_COMMIT` manifest fallback and AST source verifier |
| Documentation overstated mock/mic readiness | Critical | Rewritten with explicit PASS/BLOCKED status and manual mic gate |

## Environment observed during implementation

- Python available: 3.13.5; project supports `<3.13`.
- `uv`: 0.10.0.
- Node: 22.16.0; npm: 10.9.2.
- Docker: unavailable.
- Network/DNS from shell: unavailable.
- Pipecat/aiortc/Google/Silero runtime dependencies: not installed.
- Browser microphone/physical audio: unavailable to terminal sandbox.

Because of these constraints, application logic and source contracts were tested, but real WebRTC media, cloud voice, npm build and Docker could not be marked PASS.

## Final hardening

- Added one-worker-per-session enforcement to prevent duplicate media/context pipelines.
- Added cleanup of peer connections after worker callback failure.
- Browser now closes failed bootstrap sessions and filters duplicate word-level bot output.
- Cloud profile probe now runs correctly as a direct script and reports missing credentials without an import traceback.
