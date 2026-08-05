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

# Install NVIDIA CUDA 12 runtime libs for ctranslate2 (faster-whisper) GPU acceleration if GPU is present
if command -v nvidia-smi &>/dev/null; then
  echo "🟢 NVIDIA GPU detected. Installing CUDA 12 & cuDNN runtime for faster-whisper..."
  uv pip install --python .venv-hybrid/bin/python \
    nvidia-cublas-cu12 \
    nvidia-cudnn-cu12
fi

uv venv .venv-piper --python "$PYTHON_VERSION"
uv pip install --python .venv-piper/bin/python "piper-tts[http]==${PIPER_VERSION}"
mkdir -p models/piper
.venv-piper/bin/python -m piper.download_voices \
  --data-dir models/piper "$PIPER_VOICE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[PASS] Hybrid Linux environments installed successfully!"
echo ""
echo "📌 System Dependencies (Ubuntu/Debian):"
echo "   sudo apt-get update && sudo apt-get install -y libgomp1 libsndfile1 ffmpeg"
echo ""
echo "💡 For NVIDIA GPU acceleration (.env config):"
echo "   WHISPER_DEVICE=cuda"
echo "   WHISPER_COMPUTE_TYPE=float16"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


