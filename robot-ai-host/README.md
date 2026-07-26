# Robot AI Host Server

Pipecat v1.6.0 host for Vietnamese robot voice conversations. The project supports three runtime profiles:

| Profile | STT | LLM | TTS | Purpose |
|---|---|---|---|---|
| `mock` | scripted test double | mock | sentence tone | deterministic tests |
| `google_vi` | Google Cloud | configurable OpenAI-compatible endpoint | Google Cloud | cloud comparison |
| `hybrid_local_vi` | Whisper local | configurable OpenAI-compatible endpoint | Piper local | only LLM may cost money |

## Hybrid architecture

```text
Browser/robot microphone
→ Pipecat SmallWebRTC
→ Silero VAD
→ Whisper local
→ OpenAI-compatible LLM endpoint
→ sentence-level Piper HTTP TTS
→ browser/robot speaker
```

The endpoint, token and model are environment settings, not source-code constants:

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-with-token
LLM_MODEL=gpt-4.1
LLM_DEFAULT_HEADERS_JSON={}
```

Any service implementing the OpenAI Chat Completions-compatible API can be selected by changing these values and restarting the host.

## Quick start: Apple Silicon macOS

```bash
cp .env.hybrid.example .env
# Edit LLM_BASE_URL, LLM_API_KEY and LLM_MODEL.

./scripts/install_hybrid_macos.sh
```

Terminal 1:

```bash
./scripts/run_piper.sh
```

Terminal 2:

```bash
.venv-hybrid/bin/python scripts/check_hybrid_profile.py --profile hybrid_local_vi
./scripts/run_hybrid_host.sh
```

Browser:

```text
http://127.0.0.1:8000/client
```

Full instructions: [HYBRID_DEPLOYMENT.md](HYBRID_DEPLOYMENT.md).

## Linux

```bash
cp .env.hybrid.example .env
./scripts/install_hybrid_linux.sh
./scripts/run_piper.sh
./scripts/run_hybrid_host.sh
```

## Base tests

```bash
uv sync --frozen
uv run pytest -q
npm test --prefix clients/browser
```

## Hybrid configuration check

```bash
.venv-hybrid/bin/python scripts/check_hybrid_profile.py \
  --profile hybrid_local_vi
```

Add `--load-stt` only when you intentionally want to download/load the selected Whisper model.

## Docker Linux baseline

```bash
cp .env.hybrid.example .env
docker compose -f docker-compose.hybrid.yml up --build
```

## Security

- Never put `LLM_API_KEY` in browser code, API payloads or Git.
- `.env` and service-account files are ignored.
- `LLM_DEFAULT_HEADERS_JSON` is server-side only.
- Change `PROVISIONING_SECRET` and `JWT_SECRET_KEY` before LAN deployment.

## Upstream

- Pipecat repository: `https://github.com/pipecat-ai/pipecat`
- Tag/package: `v1.6.0` / `pipecat-ai==1.6.0`
- Browser uses the official Pipecat Client SDK and SmallWebRTC transport.

## Current verification status

Source/config tests pass in the provided environment. Optional local model packages, Piper model download, Docker, physical microphone and live LLM inference require network/hardware on the target machine and must be accepted there. See [TEST_EVIDENCE.md](TEST_EVIDENCE.md).


## Local GLM gateway preset

A ready-to-use preset is included for an OpenAI-compatible gateway at `http://127.0.0.1:20128/v1` using model `opencode-go/glm-5.1`. The API token is never committed.

```bash
cp .env.glm-local.example .env
.venv-hybrid/bin/python scripts/configure_glm_local.py
.venv-hybrid/bin/python scripts/check_llm_endpoint.py
./scripts/run_piper.sh
./scripts/run_glm_local_hybrid.sh
```

See [GLM_LOCAL_ENDPOINT.md](GLM_LOCAL_ENDPOINT.md).
