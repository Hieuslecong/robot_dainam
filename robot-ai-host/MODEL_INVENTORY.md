# MODEL_INVENTORY

Date: 2026-07-26 (Phase 0 upgrade round)

| Model | Role | Identifier | Revision | Checksum | Location |
|---|---|---|---|---|---|
| Whisper large-v3-turbo q4 (MLX) | STT default (`stt_fast_vi` candidate) | `mlx-community/whisper-large-v3-turbo-q4` | HF snapshot `660c343bbf4e52ac257f0b7d952e5388e6f93bef` | per-file hashes in HF cache | `~/.cache/huggingface/hub` |
| Faster-Whisper large-v3-turbo ct2 | STT non-Apple fallback | `deepdml/faster-whisper-large-v3-turbo-ct2` | not downloaded on this host | — | HF (runtime download) |
| Piper voice vi_VN | TTS fallback / opener tier | `vi_VN-vais1000-medium` | n/a (single release) | onnx `ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab`; json `fafb9da1354ed4b77c31af228ed41fb41cd825c14cffa105454b25e6ae751ee0` | `models/piper/` |
| Silero VAD | VAD | bundled via `pipecat-ai[silero]` 1.6.0 | pinned by uv.lock | — | site-packages |
| LLM | dialogue | via `LLM_BASE_URL`/`LLM_MODEL` env — no model shipped | — | — | external gateway |
| Whisper large-v3-turbo 8-bit MLX | STT `stt_balanced_vi` candidate | `mlx-community/whisper-large-v3-turbo-8bit` | HF snapshot `62103fc276a35fdc76e318f314d8ff47987fba89` | per-file hashes in HF cache | `~/.cache/huggingface/hub` |
| PhoWhisper-medium CT2 | STT `stt_accurate_vi` candidate | `diepho/PhoWhisper-medium-ct2` | HF snapshot `7ab76fc86fdf36847c091c08850ded2daffb66d7` | per-file hashes in HF cache | `~/.cache/huggingface/hub` |
| Whisper large-v3 8-bit MLX | STT `stt_research_vi` candidate | `mlx-community/whisper-large-v3-8bit` | HF snapshot `7fede54fd97b154a4f5e476646484fc023b1bcdf` | per-file hashes in HF cache | `~/.cache/huggingface/hub` |
| Zipformer VI int8 (sherpa-onnx) | STT `stt_streaming_vi` candidate (benchmark-only) | `csukuangfj/sherpa-onnx-zipformer-vi-int8-2025-04-20` | HF snapshot `b2745a435379992ad3f299635468db0c34918e1e` | per-file hashes in HF cache | `~/.cache/huggingface/hub` |
| VieNeu-TTS v3 Turbo | TTS expressive tier candidate | `pnnbao-ump/VieNeu-TTS-v3-Turbo` (+ codec `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`) | runtime download via `vieneu` 3.2.3 SDK | — | `~/.cache/huggingface/hub` |
| VIVOS test corpus | STT round-1 benchmark data | `AILAB-VNUHCM/vivos` (dataset) | HF snapshot `3cbfb2502e5e84776b4b778b020a09759f723f52` | — | `~/.cache/huggingface/hub` |

## Planned (not downloaded — do not claim present)

- VieNeu-TTS 0.3B quantized (`lightweight_local_vi`) — only if expressive tier misses gate.
- Qwen-Audio-3.0-TTS (cloud, opt-in Plan B — spec 16.1).

Each becomes an inventory row with revision + checksum only after actual download and verification.
