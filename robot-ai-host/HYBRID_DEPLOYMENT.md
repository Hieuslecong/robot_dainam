# Hybrid Local Voice Deployment

Profile `hybrid_local_vi` implements:

```text
Microphone → SmallWebRTC → Silero VAD → local Whisper STT
→ configurable OpenAI-compatible LLM → Piper HTTP TTS local → speaker
```

Only the LLM endpoint can require a paid API. Audio stays on the host for STT/TTS.

## 1. Configure the LLM endpoint and token

Copy the Hybrid template:

```bash
cp .env.hybrid.example .env
```

The following values may be changed without editing source code:

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-with-token
LLM_MODEL=gpt-4.1
LLM_DEFAULT_HEADERS_JSON={}
```

Examples:

```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-proj-...
LLM_MODEL=gpt-4.1

# Ollama OpenAI-compatible endpoint
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=local
LLM_MODEL=qwen2.5:7b

# vLLM OpenAI-compatible endpoint
LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_API_KEY=local-token
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# Gateway needing an additional header
LLM_DEFAULT_HEADERS_JSON={"X-Tenant":"robot-lab"}
```

`LLM_API_KEY` is passed as the OpenAI-compatible Bearer token. Do not expose it through the browser or session API. Restart the host after changing `.env`.

Legacy `OPENAI_API_KEY` and `OPENAI_MODEL` remain supported as fallbacks.

## 2. Apple Silicon macOS

Install Python environments, Pipecat local Whisper extras, Piper 1.5.0 and the Vietnamese voice:

```bash
./scripts/install_hybrid_macos.sh
```

This creates:

```text
.venv-hybrid  # Robot host + Pipecat + Faster-Whisper + MLX Whisper
.venv-piper   # isolated Piper HTTP sidecar
models/piper  # vi_VN-vais1000-medium voice
```

Start Piper in terminal 1:

```bash
./scripts/run_piper.sh
```

Validate the profile in terminal 2:

```bash
.venv-hybrid/bin/python scripts/check_hybrid_profile.py \
  --profile hybrid_local_vi
```

Start the host:

```bash
./scripts/run_hybrid_host.sh
```

Open:

```text
http://127.0.0.1:8000/client
```

`LOCAL_STT_BACKEND=auto` selects MLX on Apple Silicon. Explicit selection:

```env
LOCAL_STT_BACKEND=mlx
WHISPER_MLX_MODEL=mlx-community/whisper-large-v3-turbo-q4
```

## 3. Linux / NVIDIA / CPU

Install:

```bash
./scripts/install_hybrid_linux.sh
```

CPU baseline:

```env
LOCAL_STT_BACKEND=faster-whisper
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

NVIDIA baseline:

```env
LOCAL_STT_BACKEND=faster-whisper
WHISPER_MODEL=deepdml/faster-whisper-large-v3-turbo-ct2
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

Then run Piper and the host using the same scripts.

## 4. Docker Linux baseline

Copy `.env.hybrid.example` to `.env`, then set the LLM values. Run:

```bash
docker compose -f docker-compose.hybrid.yml up --build
```

The Docker profile uses Faster-Whisper CPU `int8` by default. It is a reproducible Linux baseline, not an Apple MLX deployment.

## 5. Piper configuration

Default:

```env
PIPER_BASE_URL=http://127.0.0.1:5000
PIPER_VOICE=vi_VN-vais1000-medium
PIPER_REQUEST_TIMEOUT_SECONDS=20
```

The Piper sidecar is deliberately separate from the Robot Host process. If Piper crashes or is restarted, the host remains isolated and reports a TTS error.

## 6. Session limit

Local Whisper loads a substantial model into memory. Default:

```env
LOCAL_STT_MAX_SESSIONS=1
```

Do not increase this to four until RAM, inference latency and model loading have been measured. The REST control plane still supports four sessions; the Hybrid voice profile applies the stricter local-model limit.

## 7. Acceptance test

1. Start Piper.
2. Run `check_hybrid_profile.py`.
3. Start the Robot Host.
4. Open `/client` and allow microphone access.
5. Say: `Tên tôi là Minh Hiếu.`
6. Verify the transcript comes from Whisper, not the mock script.
7. Verify the response is produced by the configured LLM endpoint.
8. Verify Piper speaks Vietnamese through the computer speaker.
9. Speak while the bot is talking and confirm Pipecat interruption stops stale audio.
10. Check `/v1/metrics` and `artifacts/runtime-metrics.jsonl`.

## 8. Important limitations

- Pipecat local Whisper is segmented STT, not word-by-word cloud streaming STT.
- The first run downloads Whisper and Piper models and can be slow.
- `vi_VN-vais1000-medium` is suitable for a baseline but must be evaluated for names, abbreviations and mixed Vietnamese/English speech.
- Manual microphone, audio playback, model quality and latency still require testing on the target machine.
