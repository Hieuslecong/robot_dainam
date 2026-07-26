# CHANGELOG REVIEW — Robot AI Host Hybrid GLM

## Round 1: Endpoint/API Compatibility

### Finding 1: GLM-5.1 thinking mode dominates streaming
- **Severity**: MEDIUM
- **Root cause**: GLM-5.1 is a reasoning model; 95% of streaming SSE chunks are `reasoning_content`, only ~5% are `content`
- **Files changed**: None (model behavior, not fixable in our code)
- **Fix**: Documented limitation. Voice pipeline sentence aggregator will wait for content tokens; first audio delayed by ~2s
- **Test evidence**: `check_llm_endpoint.py` PASS, 33 SSE events, first event at 2052ms
- **Limitation**: No `no-think` variant available on gateway

### Finding 2: Gateway does not require auth
- **Severity**: LOW (localhost-only)
- **Root cause**: Gateway at 127.0.0.1:20128 accepts requests without Authorization header
- **Files changed**: `.env` — set `LLM_API_KEY=local-gateway-no-auth-required` (placeholder)
- **Fix**: Not required for local dev; note in deployment docs

### Finding 3: /v1/models returns 693 entries
- **Severity**: NONE
- **Root cause**: Gateway proxies multiple providers; all models visible
- **Files changed**: None
- **Fix**: `opencode-go/glm-5.1` present among entries; filtering not needed

## Round 2: Pipecat/Audio Correctness
(In progress — requires manual mic-loa test)

## Known Issues Fixed
### Fix 1: Static assets 404
- **Finding**: HTML referenced `/assets/...` but server mounts at `/client`
- **Severity**: HIGH (client page broken)
- **Files changed**: `clients/browser/vite.config.js` (new)
- **Fix**: Set Vite `base: '/client/'`, rebuild

### Fix 2: Missing pipecat-ai[piper] extra
- **Finding**: `No module named 'piper'` when creating PiperHttpTTSService
- **Severity**: HIGH (TTS service fails to import)
- **Files changed**: None (runtime install)
- **Fix**: `uv pip install pipecat-ai[piper]==1.6.0`

### Fix 3: JWT key too short
- **Finding**: HMAC key 24 bytes < recommended 32 for SHA256
- **Severity**: LOW (dev only)
- **Files changed**: `.env` JWT_SECRET_KEY
- **Fix**: Extended to 32 bytes

## Test regression
- Python: 89/90 pass (1 pre-existing .env conflict)
- Frontend: 4/4 pass
- LLM endpoint: 3/3 checks pass
- Hybrid profile: 7/7 checks pass
- Whisper: transcription verified
- Piper: synthesis + playback verified
