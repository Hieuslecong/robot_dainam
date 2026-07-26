#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This installer is for Apple Silicon macOS. Use install_hybrid_linux.sh elsewhere." >&2
  exit 2
fi

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PIPER_VERSION="${PIPER_VERSION:-1.5.0}"
PIPER_VOICE="${PIPER_VOICE:-vi_VN-vais1000-medium}"

uv python install "$PYTHON_VERSION"
UV_PROJECT_ENVIRONMENT=.venv-hybrid uv sync --frozen --python "$PYTHON_VERSION"
uv pip install --python .venv-hybrid/bin/python \
  'pipecat-ai[whisper,mlx-whisper]==1.6.0'

uv venv .venv-piper --python "$PYTHON_VERSION"
uv pip install --python .venv-piper/bin/python "piper-tts[http]==${PIPER_VERSION}"
mkdir -p models/piper
.venv-piper/bin/python -m piper.download_voices \
  --data-dir models/piper "$PIPER_VOICE"

echo "[PASS] Hybrid macOS environments installed."
echo "Start Piper: scripts/run_piper.sh"
echo "Start host:  scripts/run_hybrid_host.sh"
