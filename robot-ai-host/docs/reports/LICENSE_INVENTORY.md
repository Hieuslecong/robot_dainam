# LICENSE_INVENTORY

Date: 2026-07-26 (Phase 0 upgrade round)

Status values: VERIFIED (license file/text read), REPORTED (registry metadata only), NOT VERIFIED.
No commercial-distribution claim is made for anything below VERIFIED. Legal review before
distribution is a HUMAN_TASK_CHECKLIST item.

| Component | License | Status | Note |
|---|---|---|---|
| pipecat-ai 1.6.0 | BSD-2-Clause | REPORTED (PyPI metadata) | read LICENSE in package before distribution |
| fastapi | MIT | REPORTED | |
| uvicorn | BSD-3-Clause | REPORTED | |
| pydantic / pydantic-settings | MIT | REPORTED | |
| structlog | MIT/Apache-2.0 dual | REPORTED | |
| python-dotenv | BSD-3-Clause | REPORTED | |
| PyJWT | MIT | REPORTED | |
| httpx | BSD-3-Clause | REPORTED | |
| pyyaml | MIT | REPORTED | |
| @pipecat-ai/client-js, small-webrtc-transport | BSD-2-Clause | REPORTED (npm) | |
| vite | MIT | REPORTED | dev-only |
| Piper (rhasspy/piper runtime) | MIT | REPORTED | |
| Piper voice `vi_VN-vais1000-medium` | **NOT VERIFIED** | NOT VERIFIED | voice dataset/training origin unknown; must verify before distribution |
| whisper-large-v3-turbo (OpenAI weights) | Apache-2.0 | REPORTED | |
| mlx-community q4 conversion | **NOT VERIFIED** | NOT VERIFIED | conversion repo license must be read |
| Silero VAD | MIT | REPORTED | |

## Phase 1 additions (downloaded this round)

| Component | License | Status | Note |
|---|---|---|---|
| VieNeu-TTS v3 Turbo (`pnnbao-ump/VieNeu-TTS-v3-Turbo`) | Apache-2.0 | REPORTED (HF model card front-matter read) | voice-cloning feature NOT used; default built-in voices only. Reference-voice consent (spec 16.4) n/a until cloning is enabled |
| MOSS-Audio-Tokenizer-Nano (codec, OpenMOSS-Team) | **NOT VERIFIED** | NOT VERIFIED | pulled at runtime by vieneu SDK — read license before distribution |
| `vieneu` 3.2.3 SDK + sea-g2p | **NOT VERIFIED** | NOT VERIFIED | check PyPI/GitHub license |
| PhoWhisper-medium (VinAI weights, `diepho/PhoWhisper-medium-ct2` conversion) | **NOT VERIFIED** | NOT VERIFIED | PhoWhisper upstream is BSD-3-Clause per VinAI repo (REPORTED); the CT2 conversion repo's own license must be read |
| `mlx-community/whisper-large-v3-turbo-8bit`, `whisper-large-v3-8bit` | **NOT VERIFIED** | NOT VERIFIED | base weights Apache-2.0; conversion repos must be read |
| sherpa-onnx runtime + `sherpa-onnx-zipformer-vi-int8-2025-04-20` | Apache-2.0 | REPORTED (k2-fsa project) | model card must be read for training-data terms |
| VIVOS corpus | CC BY-NC-SA 4.0 | REPORTED | benchmark use only — NON-COMMERCIAL clause: fine for internal evaluation, do NOT ship corpus |
| jiwer, soundfile, psutil | Apache-2.0 / BSD / BSD | REPORTED | benchmark-only deps |

## Still planned — license check BEFORE adoption

- VieNeu-TTS 0.3B quantized: only if adopted.
- Qwen-Audio-3.0-TTS cloud: API terms + data-processing location (Singapore) — verify; privacy notice required (spec 16.1).
