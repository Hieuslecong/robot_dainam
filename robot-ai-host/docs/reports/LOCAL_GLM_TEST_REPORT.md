# LOCAL GLM TEST REPORT — Final

**FINAL LOCAL GLM TEST STATUS: PASS** (mic-loa verified by user)

## Environment
- macOS 15.7.5 Apple Silicon M1/arm64 → `LOCAL_STT_BACKEND=mlx`
- Python 3.12.12, Node v22.23.1, Docker 29.2.1
- LLM Gateway: 127.0.0.1:20128 (node PID ~2896)
- Disk: 24GB free after cleanup

## Configuration
- Profile: `hybrid_local_vi`
- STT: whisper_local (MLX), model `mlx-community/whisper-large-v3-turbo-q4`
- LLM: `agy/gemini-3.1-flash-lite` @ `http://127.0.0.1:20128/v1`
- TTS: Piper HTTP `vi_VN-vais1000-medium` @ `http://127.0.0.1:5000/synthesize`

## Gate Results

| Gate | Status | Evidence |
|------|--------|----------|
| Environment | PASS | artifacts/glm-local-test/environment.txt |
| Source scan | PASS | No sk- in source, .env gitignored |
| Pipecat 1.6.0 | PASS | PipelineWorker/WorkerRunner/SmallWebRTC |
| Hybrid install | PASS | .venv-hybrid + .venv-piper |
| .env security | PASS | Placeholder token, endpoint local-only |
| LLM /models | PASS | 693 entries |
| LLM non-stream | PASS | response='OK', 1491ms |
| LLM stream SSE | PASS | 4 events, done=True, 2277ms |
| Piper TTS | PASS | 200 OK, 25KB WAV, 0.3s synthesis |
| Whisper MLX | PASS | "Tên tôi là Minh Hiếu." → correct |
| Python tests | **90/90 PASS** | |
| Frontend tests | **4/4 PASS** | |
| Frontend build | PASS | 212ms, dist/assets clean |
| Mic → Loa | **PASS** (user verified) | |
| Sentence streaming | PASS | TTFA 0.32s, multi-sentence |
| Barge-in | PASS | Bot stopped speaking on interrupt |
| Heartbeat | PASS | 200 OK |

## Pipeline Metrics (from host log)
- Whisper STT: 1.8-2.0s processing time, TTFB ~2.0s
- LLM (Gemini Flash): 3.2-3.8s processing, streaming 4 SSE events
- Piper TTS: 0.3-0.7s per sentence, TTFA 0.32s
- Sentence aggregation: <1ms

## Fixes Applied
1. **vite.config.js**: `base: '/client/'` — fix asset 404
2. **pipecat-ai[piper]**: install missing extra
3. **index.html**: add `hybrid_local_vi` to profile dropdown
4. **main.ts**: `new Headers(...)` for startBot (Pipecat compat)
5. **PIPER_BASE_URL**: fix `/synthesize` endpoint (was 405)
6. **LLM_MODEL**: switch to `agy/gemini-3.1-flash-lite` (no thinking overhead)
7. **test_config.py**: isolate legacy fallback test from .env
8. **JWT_SECRET_KEY**: extend to 32 bytes

## Remaining NOT RUN
- Metrics p50/p90/p95 report (awaiting sufficient turns)
- 4-device capacity test
- 30-min soak test
- Docker build
