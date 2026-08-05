# DEPENDENCY_LOCK_REPORT

Date: 2026-07-26 (Phase 0 upgrade round)

## Python

- Manager: uv. `pyproject.toml` pins direct ranges; `uv.lock` (95 packages) pins exact versions + hashes.
- Canonical install: `uv sync --frozen`. Canonical test: `uv run pytest -q`.
- Python requirement: `>=3.11,<3.13` (venvs run cpython 3.12.x).

Direct dependencies (locked versions from `uv export --frozen`):

| Package | Declared | Locked |
|---|---|---|
| pipecat-ai[webrtc,google,silero] | ==1.6.0 | 1.6.0 |
| fastapi | >=0.115,<1 | 0.139.2 |
| uvicorn[standard] | >=0.34,<1 | 0.51.0 |
| pydantic | >=2.0,<3 | 2.13.4 |
| pydantic-settings | >=2.0,<3 | 2.14.2 |
| structlog | >=24.0,<25 | 24.4.0 |
| python-dotenv | >=1.0,<2 | 1.2.2 |
| PyJWT | >=2.8,<3 | 2.13.0 |
| httpx | >=0.27,<1 | 0.28.1 |
| pyyaml | >=6.0,<7 | 6.0.3 |
| pytest / pytest-asyncio / coverage (dev) | >=8.0 / >=0.24 / >=7.0 | per uv.lock |

Note: `.venv-hybrid` additionally carries STT extras (mlx-whisper on Apple Silicon) installed by
`scripts/install_hybrid_macos.sh`; these are runtime-profile extras, not in the base lock. Phase 1
will pin them when STT profiles land.

## Frontend (clients/browser)

- Manager: npm, `package-lock.json` present (lockfileVersion 3, exact versions + integrity hashes).
- Direct deps: `@pipecat-ai/client-js` 1.12.0, `@pipecat-ai/small-webrtc-transport` 1.10.5; dev: `vite` 8.0.16.
- Canonical install: `npm ci --prefix clients/browser`.

## Reproducibility gaps (honest)

- Hybrid venv STT extras not lock-pinned yet (Phase 1 scope).
- Piper runs from `.venv-piper` (piper-tts) — version pinned by that venv, not by a lock file; record in Phase 2 TTS work.
