# Robot AI Host — Technical Specification & Upgrade Blueprint

> Version: 0.2.0 | Date: 2026-07-26 | Author: Principal Realtime Voice AI Engineer  
> Repository: `/Users/minhhieu/Downloads/robot_dainam/robotv1/robot-ai-host`

---

## 1. SYSTEM OVERVIEW

Real-time voice assistant pipeline for Vietnamese. Runs on macOS Apple Silicon (M1).  
Architecture: browser client → WebRTC → Pipecat pipeline → local TTS sidecar.

```
Microphone (Chrome/Safari)
  → WebRTC (SmallWebRTC)
    → Whisper STT (MLX, Apple GPU)
      → Silero VAD + Smart Turn V3
        → Gemini Flash Lite (OpenAI-compatible gateway)
          → Sentence Aggregator
            → StreamDeduplicator
              → ResponsePolicy (max 3 sentences / 80 words)
                → Piper TTS (HTTP sidecar, port 5001)
                  → Speaker
```

---

## 2. COMPONENT INVENTORY

### 2.1 Core Infrastructure

| Component | Technology | Version | Location |
|-----------|-----------|---------|----------|
| Python runtime | CPython | 3.12.12 | `.venv-hybrid/` |
| ASGI server | Uvicorn | latest | `app.main:create_app()` |
| Web framework | FastAPI | latest | `app/main.py` |
| Voice framework | Pipecat | 1.6.0 | `.venv-hybrid` |
| Browser client | Vite + TypeScript | 8.0.16 | `clients/browser/` |
| Client SDK | @pipecat-ai/client-js | 1.12.0 | `node_modules/` |
| Transport | SmallWebRTC | bundled | Pipecat + client JS |
| GPU compute | PyTorch MPS + MLX | latest | system-level |
| LLM gateway | OpenAI-compatible | - | `127.0.0.1:20128/v1` |
| Config format | YAML | - | `config/profiles.yaml` |
| Settings | pydantic-settings | latest | `app/config.py` |

### 2.2 Speech-to-Text (STT)

| Attribute | Current Value |
|-----------|---------------|
| Backend | MLX (Apple Neural Engine) |
| Model | `mlx-community/whisper-large-v3-turbo-q4` |
| Quantization | 4-bit (q4) |
| Language | Vietnamese (vi) |
| Model size | ~400MB |
| Processing time | 1.7–2.0s |
| Accuracy issue | Moderate — q4 loss hurts Vietnamese diacritics |

**Configuration** (`config/profiles.yaml` → `stt`):
```yaml
stt:
  backend: mlx
  model: whisper-large-v3-turbo-q4
```

**Relevant env vars**:
```
LOCAL_STT_BACKEND=auto  # resolves to "mlx" on Apple Silicon
WHISPER_NO_SPEECH_PROB=0.6
WHISPER_TEMPERATURE=0.0
```

### 2.3 Large Language Model (LLM)

| Attribute | Current Value |
|-----------|---------------|
| Provider | OpenAI-compatible gateway |
| Endpoint | `http://127.0.0.1:20128/v1` |
| **Current model** | `agy/gemini-3.1-flash-lite` |
| Previous model | `opencode-go/glm-5.1` (replaced — thinking overhead) |
| Failed model | `opencode-go/deepseek-v4-flash` (replaced — thinking model, content empty) |
| Temperature | 0.2 |
| Max tokens | 160 |
| Streaming | Enabled |
| TTFB (P50) | ~2.2s |
| Total latency | ~4.0s |
| Token overhead | ~2300 prompt tokens per turn |

**System prompt** (`app/core/system_prompt.py` → `build_system_prompt()`):
- "Bạn là Trợ lý nhà trường, trợ lý cá nhân và trợ lý nhà trường."
- Prohibits: Antigravity, Google DeepMind, OpenAI, programmer persona
- Max response: 3 sentences, 80 words
- Source: `config/assistant_school.yaml`

**⚠️ Known issue**: Thinking models (`glm-5.1`, `deepseek-v4-flash`) route all tokens to `reasoning_content`, leaving `content` empty → TTS silent. Only non-thinking models work for voice.

**Configuration** (`app/config.py` → `Settings`):
```python
llm_temperature: float = 0.2
llm_max_tokens: int = 160
llm_stream: bool = True
llm_runtime_hint: str = "unknown"
```

### 2.4 Text-to-Speech (TTS)

| Attribute | Current Value |
|-----------|---------------|
| Engine | Piper HTTP (sidecar) |
| Model | `vi_VN-vais1000-medium` |
| Endpoint | `http://127.0.0.1:5001/synthesize` |
| Format | WAV, 16kHz mono |
| TTFA (P50) | ~306ms |
| Quality | Acceptable — robotic tone, no emotion |
| Emotion tags | Not supported |
| GPU | CPU (ONNX — no Metal backend) |

**⚠️ Port conflict**: Port 5000 is claimed by AirPlay/AirTunes on macOS. Piper runs on **port 5001**.

### 2.5 Voice Activity & Turn Management

| Component | Technology |
|-----------|-----------|
| VAD | Silero VAD (ONNX) |
| Turn detection | Pipecat Smart Turn V3 (ONNX) |
| Parameters | confidence=0.7, start_secs=0.2, stop_secs=0.2, min_volume=0.6 |
| Barge-in | Supported — broadcasts interruption frame |

### 2.6 Processors (Pipeline Middleware)

| Processor | File | Role |
|-----------|------|------|
| `STTGuard` | `app/processors/stt_guard.py` | Filter partial transcripts, echo, duplicates, short speech |
| `StreamDeduplicator` | `app/processors/stream_deduplicator.py` | Drop duplicate sentences via hash + TTL |
| `ResponsePolicyProcessor` | `app/processors/response_policy.py` | Truncate to max sentences/words at sentence boundary |
| `VietnameseSpeechTextFilter` | `app/pipecat_runtime/text_filter.py` | Remove Markdown/URLs before TTS |

### 2.7 Device & Acceleration

| Component | File | Role |
|-----------|------|------|
| `DeviceManager` | `app/core/device_manager.py` | Detect MPS/MLX/CUDA/CPU |
| `check_acceleration.py` | `scripts/check_acceleration.py` | Prove MPS/MLX via actual inference |

**Current device status** (M1 MacBook Air):
```
Platform:      Darwin arm64
PyTorch device: mps (Apple GPU)
STT backend:   mlx (Apple Neural Engine)
TTS backend:   piper-http-mps (label only — actually CPU)
MLX available: True
Fallbacks:     []
```

### 2.8 Frontend

| Attribute | Value |
|-----------|-------|
| Framework | Vite 8 + vanilla TypeScript |
| Entry | `clients/browser/src/main.ts` |
| Profiles | `hybrid_local_vi`, `google_vi`, `mock` |
| WebRTC library | `@pipecat-ai/small-webrtc-transport` |
| Base path | `/client/` (configured in `vite.config.js`) |
| Build output | `clients/browser/dist/` (426KB JS + 3.5KB CSS) |

### 2.9 APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/v1/profiles` | GET | List available profiles |
| `/v1/devices/register` | POST | Register device → JWT token |
| `/v1/sessions` | POST | Create session → webrtcUrl |
| `/v1/sessions/{id}/api/offer` | POST | WebRTC SDP exchange |
| `/v1/sessions/{id}/heartbeat` | POST | Keep-alive |
| `/v1/metrics` | GET | Latency metrics (JSON) |
| `/api/system/devices` | GET | Device diagnostics (JSON) |
| `/api/settings` | POST | Save LLM config to .env |
| `/settings` | GET | Settings UI (HTML) |
| `/client/` | GET | Voice client (SPA) |

### 2.10 Security

| Measure | Status |
|---------|--------|
| API key not in source | ✅ `.env` only (.gitignored) |
| API key not in logs | ✅ log masks applied |
| Settings page binds localhost | ✅ `host=127.0.0.1` |
| Bearer token auth | ✅ JWT for device sessions |
| No token committed | ✅ `.env.local` + `.env` both gitignored |

---

## 3. KNOWN LIMITATIONS

### 3.1 STT Accuracy

| Issue | Root Cause | Severity |
|-------|-----------|----------|
| Vietnamese diacritic errors | `q4` quantization loss | **High** |
| Background noise leaked | No AEC (acoustic echo cancellation) | Medium |
| Short utterances missed | `min_speech_ms=300` may be too high | Low |
| LLM response context | Context accumulates without capping | Medium |

### 3.2 TTS Quality

| Issue | Root Cause | Severity |
|-------|-----------|----------|
| Robotic, monotone voice | Piper VITS — single speaker, no prosody | **High** |
| No emotion/expressiveness | Piper doesn't support emotion tags | **High** |
| Truncated audio on barge-in | Stale TTS context cleaned correctly | Low |
| Port 5000 conflict | macOS AirPlay claims 5000 | Fixed (→5001) |

### 3.3 LLM

| Issue | Root Cause | Severity |
|-------|-----------|----------|
| High TTFB (~2s) | Remote gateway latency | Medium |
| Thinking models silent | `reasoning_content` consumes all tokens | Fixed (use non-thinking) |
| Context window growing | No max turn cap in LLMContext | Medium |
| No tool calling | LLM can't query school database | Feature gap |

### 3.4 Pipeline

| Issue | Root Cause | Severity |
|-------|-----------|----------|
| LLM response sometimes empty | Deep thinking models | Fixed (model selection) |
| No conversation reset UI | No reset button in client | Low |
| Metrics incomplete | Some Pipecat metrics unused | Low |
| No Docker support | Dev setup is manual | Medium |

---

## 4. UPGRADE ROADMAP

### 4.1 Immediate (Week 1) — Quality of Life

| Task | File | Effort |
|------|------|--------|
| **Upgrade Whisper model** `q4 → turbo` | `.env` / `config/profiles.yaml` | 5 min |
| **Upgrade Piper voice** `medium → high` | `.env` | 5 min |
| **Add conversation max turns** (10) | `config.py` + `pipeline_factory.py` | 30 min |
| **Add conversation reset button** | `main.ts` + backend endpoint | 1 hour |
| **Fix dual utterance bug** (`Bạn là ai` + `em quan trọng lời mượt`) | Investigate VAD sensitivity | 2 hours |

### 4.2 Week 2 — TTS Upgrade (Emotion & Naturalness)

| Task | Effort |
|------|--------|
| **Integrate Kokoro TTS** as alternative backend | 4 hours |
| Add emotion tag support (`[happy]`, `[sad]`) in system prompt | 1 hour |
| Pipeline: Kokoro primary → Piper fallback | 2 hours |
| A/B test voice quality with real users | 1 hour |

### 4.3 Week 3 — Accuracy & Intelligence

| Task | Effort |
|------|--------|
| **Add AEC** (echo cancellation) in WebRTC transport | 4 hours |
| **Add LLM model auto-detect** (probe for thinking vs normal) | 3 hours |
| **Knowledge base loader** (read `knowledge/*.md` into context) | 3 hours |
| **Tool calling** for school data queries | 8 hours |

### 4.4 Month 2 — Production

| Task | Effort |
|------|--------|
| Docker multi-stage build | 4 hours |
| Multi-device capacity test | 2 hours |
| 30-min soak test | 1 hour |
| CI/CD pipeline | 4 hours |
| Production hardening | 8 hours |

---

## 5. FILE MAP

```
robot-ai-host/
├── app/
│   ├── main.py                          # FastAPI server, routes
│   ├── config.py                        # pydantic-settings
│   ├── auth.py                          # JWT tokens
│   ├── sessions.py                      # Session manager
│   ├── logging_utils.py                 # Structured logger
│   ├── core/
│   │   ├── device_manager.py            # MPS/MLX/CUDA detection
│   │   └── system_prompt.py             # Prompt builder from YAML
│   ├── pipecat_runtime/
│   │   ├── pipeline_factory.py          # Pipeline creation per profile
│   │   ├── worker_factory.py            # Worker + runner lifecycle
│   │   ├── rtvi.py                      # RTVI protocol handler
│   │   ├── observers.py                 # Metrics observers
│   │   ├── metrics.py                   # Latency tracker
│   │   ├── text_filter.py               # TTS text sanitizer
│   │   └── text_sanitizer.py            # Regex filters
│   ├── processors/
│   │   ├── stt_guard.py                 # STT noise/echo filter
│   │   ├── stream_deduplicator.py       # Sentence deduplication
│   │   └── response_policy.py           # Length truncation
│   └── robot/
│       ├── messages.py
│       ├── validator.py
│       └── fake_adapter.py
├── clients/browser/
│   ├── src/main.ts                      # Voice client logic
│   ├── index.html                       # Client page
│   ├── vite.config.js                   # Base path fix
│   └── dist/                            # Built output
├── config/
│   ├── assistant_school.yaml            # Persona & capabilities
│   └── profiles.yaml                    # STT/LLM/TTS profiles
├── config/
│   └── profiles.yaml                    # Legacy (check which is active)
├── knowledge/
│   └── README.md                        # School data directory
├── scripts/
│   ├── check_acceleration.py            # MPS/MLX verification
│   ├── check_llm_endpoint.py            # LLM gateway probe
│   ├── check_hybrid_profile.py          # Profile validator
│   ├── report_latency.py                # Metrics analyzer
│   └── install_hybrid_macos.sh          # Dependency installer
├── tests/
│   ├── unit/test_config.py              # Settings tests
│   ├── unit/test_text_sanitizer.py
│   ├── integration/test_pipeline_mock.py
│   └── ...
├── reports/
│   ├── 00_current_architecture.md       # Architecture audit
│   ├── 01_root_cause_analysis.md        # Root causes
│   └── 02_before_after.md              # Before/after summary
├── .env                                 # Active config (gitignored)
├── .env.glm-local.example               # Example config
├── LOCAL_GLM_TEST_REPORT.md             # Previous test report
├── LOCAL_LATENCY_REPORT.md              # Latency analysis
└── artifacts/
    └── glm-local-test/
        ├── host.log                     # Runtime log
        └── runtime-metrics.jsonl        # Metrics records
```

---

## 6. CURRENT BENCHMARKS

### 6.1 Latency (P50, hybrid_local_vi profile)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| first_sentence | 40ms | ≤600ms | ✅ |
| tts_first_audio (TTFA) | 306ms | ≤300ms | ✅ |
| llm_first_token (TTFT) | 1911ms | ≤700ms | ⚠️ 2.7x |
| turn_end → stt_final | 1958ms | ≤700ms | ⚠️ 2.8x |
| server_user_to_bot (E2E) | 7682ms | ≤1900ms | ⚠️ 4.0x |

**Bottleneck**: LLM gateway latency dominates. Local model would improve TTFB significantly.

### 6.2 Throughput

| Metric | Value |
|--------|-------|
| Max sessions | 4 |
| Concurrent WebRTC | ~2 stable tested |
| Piper TTS | ~0.3s per sentence |
| Whisper STT | ~1.8s per utterance |

---

## 7. DEVELOPMENT COMMANDS

```bash
# Start Piper TTS (terminal 1)
PYTHONPATH=.venv-piper/bin/python -m piper.http_server \
  --host 127.0.0.1 --port 5001 --data-dir models/piper \
  -m vi_VN-vais1000-medium

# Start Voice Host (terminal 2)
PYTHONPATH=.venv-hybrid/bin/python -m app.main --profile hybrid_local_vi

# Verify acceleration
PYTHONPATH=.venv-hybrid/bin/python scripts/check_acceleration.py

# Verify LLM endpoint
PYTHONPATH=.venv-hybrid/bin/python scripts/check_llm_endpoint.py

# Run all tests
PYTHONPATH=.venv-hybrid/bin/python -m pytest tests/ -q
cd clients/browser && npm run test

# Build frontend
cd clients/browser && npm run build

# Settings page
open http://127.0.0.1:8000/settings

# Voice client
open http://127.0.0.1:8000/client/

# Device diagnostics
curl http://127.0.0.1:8000/api/system/devices
```

---

## 8. DEPENDENCIES

### Python (`.venv-hybrid`)
```
pipecat-ai==1.6.0
pipecat-ai[whisper,mlx-whisper,piper]
pydantic-settings
uvicorn[standard]
fastapi
torch (MPS)
mlx
mlx-whisper
pyyaml
aiohttp
pyjwt
```

### Node (`clients/browser/`)
```
@pipecat-ai/client-js: 1.12.0
@pipecat-ai/small-webrtc-transport: bundled
vite: 8.0.16
```

### System
- macOS 15.7.5 (arm64)
- AirPlay disabled on port 5000 (or Piper on 5001)
- Netbird LLM gateway at 127.0.0.1:20128

---

## 9. LICENSING & ATTRIBUTION

- Pipecat: BSD-3-Clause (Daily LLC)
- Whisper (MLX): MIT (Apple)
- Silero VAD: MIT
- Piper TTS: MIT
- Smart Turn V3: Pipecat bundled
