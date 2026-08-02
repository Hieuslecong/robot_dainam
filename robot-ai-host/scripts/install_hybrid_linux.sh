#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PIPER_VERSION="${PIPER_VERSION:-1.5.0}"
PIPER_VOICE="${PIPER_VOICE:-vi_VN-vais1000-medium}"

uv python install "$PYTHON_VERSION"
UV_PROJECT_ENVIRONMENT=.venv-hybrid uv sync --frozen --python "$PYTHON_VERSION"
uv pip install --python .venv-hybrid/bin/python \
  'pipecat-ai[whisper]==1.6.0' \
  faster-whisper \
  sherpa-onnx \
  huggingface_hub \
  vieneu

uv venv .venv-piper --python "$PYTHON_VERSION"
uv pip install --python .venv-piper/bin/python "piper-tts[http]==${PIPER_VERSION}"
mkdir -p models/piper
.venv-piper/bin/python -m piper.download_voices \
  --data-dir models/piper "$PIPER_VOICE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[PASS] Hybrid Linux environments installed successfully!"
echo ""
echo "📌 Note for Linux system dependencies:"
echo "   Ensure system libraries are installed (Ubuntu/Debian):"
echo "   sudo apt-get update && sudo apt-get install -y libgomp1 libsndfile1 ffmpeg"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

