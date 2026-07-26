# TEST EVIDENCE — GLM Local Hybrid

## Gate Status Summary

| Gate | Status | Evidence |
|------|--------|----------|
| Environment detection | PASS | artifacts/glm-local-test/environment.txt |
| Source & secret scan | PASS | No sk- in source; .env gitignored |
| Pipecat API version | PASS | No PipelineTask/PipelineRunner; pipecat-ai==1.6.0 |
| Hybrid install | PASS | .venv-hybrid + .venv-piper created |
| .env security | PASS | chmod 0600; token is placeholder |
| LLM /models | PASS | 693 entries; opencode-go/glm-5.1 present |
| LLM non-streaming | PASS | response='OK', model=glm-5.1 |
| LLM streaming SSE | PASS | 33 events, done=True, valid JSON |
| Piper TTS smoke | PASS | 100KB WAV, 22050Hz, playback OK |
| Whisper MLX transcription | PASS | "Tên tôi là Minh Hiếu." → correct |
| Python tests | 89/90 PASS | 1 pre-existing .env conflict |
| Frontend tests | 4/4 PASS | Source contract, no raw WebRTC |
| Frontend build | PASS | 134ms, no secrets in bundle |
| Host health | PASS | status=ok, webrtc_available=true |
| Client page | PASS | Served at /client/, assets load |
| Mic-loa test A-F | NOT RUN | Pending user interaction |
| Metrics | NOT RUN | Pending real sessions |
| Capacity (4 devices) | NOT RUN | Pending multi-session test |
| Soak test | NOT RUN | Pending 30-min run |
| Docker | NOT RUN | Pending docker-compose build |

## Artifacts Generated
```
artifacts/glm-local-test/
├── environment.txt         ✅
├── llm-endpoint.txt        ✅
├── hybrid-profile.txt      ✅
├── python-tests.txt        ✅
├── frontend-tests.txt      ✅
├── frontend-build.txt      ✅
├── piper-smoke.wav         ✅ (100KB)
├── whisper-transcript.json ✅
├── host.log                🔄 (running)
├── browser-console.log     NOT RUN
├── latency-report.txt      NOT RUN
├── capacity-report.txt     NOT RUN
└── soak.log               NOT RUN
```

## Commands to Reproduce
```bash
# Pre-flight
uv python install 3.12
bash scripts/install_hybrid_macos.sh

# Configure
cp .env.glm-local.example .env
PYTHONPATH= .venv-hybrid/bin/python scripts/check_llm_endpoint.py

# Piper (terminal 1)
PYTHONPATH= .venv-piper/bin/python -m piper.http_server \
  --host 127.0.0.1 --port 5000 --data-dir models/piper \
  -m vi_VN-vais1000-medium

# Host (terminal 2)
PYTHONPATH= .venv-hybrid/bin/python -m app.main --profile hybrid_local_vi

# Tests
PYTHONPATH= .venv-hybrid/bin/python -m pytest tests/ -q
cd clients/browser && npm ci && npm run test && npm run build

# Client
open http://127.0.0.1:8000/client/
```
