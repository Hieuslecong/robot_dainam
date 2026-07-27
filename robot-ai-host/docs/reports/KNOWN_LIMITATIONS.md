# Known Limitations

## ✅ Resolved (đã vượt qua)

1. Python 3.12 installed via uv ✅
2. pipecat-ai==1.6.0 + whisper + mlx-whisper + piper ✅
3. npm ci + Vite build successful ✅
4. LLM gateway reachable at 127.0.0.1:20128 ✅
5. Piper TTS HTTP server running ✅
6. Whisper MLX transcription verified ✅

## ⚠️ Current Limitations

### GLM-5.1 Thinking Mode
- GLM-5.1 is a reasoning model; 95% of streaming tokens are `reasoning_content`
- First `content` token arrives after ~164 reasoning chunks (~2s delay)
- Voice pipeline latency increased proportional to reasoning length
- No `no-think` variant available on gateway
- Mitigation: Sentence aggregator waits for content; first audio delayed but pipeline still functional

### Single Whisper Session
- LOCAL_STT_MAX_SESSIONS=1 limits concurrent transcription
- Multi-session capacity scoped to 1 STT session at a time
- Not a code limitation — config choice to avoid RAM exhaustion on MLX

### JWT Key
- dev-jwt-secret is 24 bytes (now 32); still dev-only, must be rotated for production
- In-memory session registry loses sessions on restart

### Test Environment Conflict
- `test_generic_llm_falls_back_to_legacy_openai_variables` fails because .env LLM_API_KEY overrides constructor args
- Pydantic-settings reads .env after constructor; test needs `_env_file=None`
- Not a code bug — test-environment conflict. Requires test isolation fix.

### Manual Mic-Loa Test Required
- Microphone, speaker, and barge-in acceptance tests require physical hardware
- Cannot be automated from terminal environment
- Must be performed by user at http://127.0.0.1:8000/client/

### Docker Baseline
- Native macOS is the priority baseline
- Docker route requires LLM_BASE_URL=http://host.docker.internal:20128/v1
- Not tested in this cycle

## Product Limitations (unchanged)
- In-memory session registry
- No long-term transcript/conversation storage
- No provider fallback
- No real robot adapter
- No camera/video
- LAN beyond localhost needs TLS + TURN
