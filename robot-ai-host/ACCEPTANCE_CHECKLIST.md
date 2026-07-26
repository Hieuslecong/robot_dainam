# Acceptance Checklist

| Requirement | Status |
|---|---|
| Hybrid profile in configuration | PASS |
| Local Whisper provider code | PASS — source/API contract |
| MLX backend selection on Apple Silicon | PASS — source/config |
| Faster-Whisper backend selection | PASS — source/config |
| Configurable LLM base URL | PASS |
| Configurable LLM token | PASS |
| Configurable LLM model | PASS |
| Optional custom LLM headers | PASS |
| Piper HTTP local TTS | PASS — source/API contract |
| Sentence-level TTS | PASS — source contract |
| Per-session Piper cleanup | PASS |
| Conservative local STT concurrency limit | PASS |
| macOS installer/launch scripts | PASS — source review |
| Linux installer/launch scripts | PASS — source review |
| Hybrid Docker baseline | PASS — source created, NOT RUN |
| Python tests | PASS — 84 passed, 1 skipped |
| Frontend source tests | PASS — 4 passed |
| Frontend production build | BLOCKED — no registry access |
| Live Whisper model | NOT RUN |
| Live Piper voice | NOT RUN |
| Live configurable LLM endpoint | NOT RUN |
| Physical microphone/speaker | NOT RUN |
| Live barge-in and latency | NOT RUN |
| Four simultaneous Hybrid voice sessions | NOT RUN; default limit is 1 |
