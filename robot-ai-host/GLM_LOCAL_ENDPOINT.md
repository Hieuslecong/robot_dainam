# Local GLM endpoint preset

This preset connects the Hybrid pipeline to an OpenAI-compatible gateway on the same machine:

```text
http://127.0.0.1:20128/v1
model: opencode-go/glm-5.1
```

The API token is intentionally not stored in this repository.

## Configure securely

```bash
.venv-hybrid/bin/python scripts/configure_glm_local.py
```

The script requests the token with hidden input and writes `.env` with mode `0600` where supported.

## Check the gateway

```bash
.venv-hybrid/bin/python scripts/check_llm_endpoint.py
```

The probe checks:

1. `GET /v1/models` when available;
2. non-streaming `POST /v1/chat/completions`;
3. streaming SSE `POST /v1/chat/completions`;
4. authentication and model selection without printing the token.

## Run the full Hybrid host

Start Piper first:

```bash
./scripts/run_piper.sh
```

Then:

```bash
./scripts/run_glm_local_hybrid.sh
```

Open:

```text
http://127.0.0.1:8000/client
```

## Docker note

When the Robot AI Host runs inside Docker, `127.0.0.1:20128` points to the container itself. On Docker Desktop use:

```env
LLM_BASE_URL=http://host.docker.internal:20128/v1
```

The native macOS/Linux baseline continues to use:

```env
LLM_BASE_URL=http://127.0.0.1:20128/v1
```
