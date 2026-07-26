# Custom GLM local gateway implementation

## Preset

```text
LLM_BASE_URL=http://127.0.0.1:20128/v1
LLM_MODEL=opencode-go/glm-5.1
```

The user token is intentionally not stored in source, documentation, examples, tests or archives.

## Added files

- `.env.glm-local.example`
- `GLM_LOCAL_ENDPOINT.md`
- `PROMPT_TEST_GLM_LOCAL.md`
- `scripts/configure_glm_local.py`
- `scripts/check_llm_endpoint.py`
- `scripts/run_glm_local_hybrid.sh`
- `scripts/test_glm_local_project.sh`
- `tests/unit/test_glm_local_preset.py`

## Capabilities

- Secure hidden token input using `getpass`.
- Atomic-like update of the local `.env` without placing token in shell history.
- Endpoint and model preset without source edits.
- `/models` compatibility probe.
- Non-streaming Chat Completions probe.
- Streaming SSE Chat Completions probe.
- Preflight checks before starting the Hybrid host.
- Automated Python/frontend contract test orchestration.
- Full manual mic, speaker, context, barge-in, metrics, capacity and soak-test prompt.
- Docker host-address guidance through `host.docker.internal`.

## Verified in the build environment

```text
Python tests: 89 passed, 1 skipped
Frontend source-contract tests: 4 passed
Python compileall: PASS
Provided token present in repository: NO
```

The skipped Python test requires the full Pipecat runtime dependency set. Live endpoint access, local Whisper/Piper inference, browser build, physical microphone/speaker and true barge-in must be executed on the target machine.
