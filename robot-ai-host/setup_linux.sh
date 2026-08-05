#!/usr/bin/env bash
# ==============================================================================
# Setup & Rebuild Script for Linux (Ubuntu/Debian)
# This script cleans existing environments and builds the entire project from scratch.
# ==============================================================================

set -euo pipefail

# Set working directory to the project root
cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Phase 1: Cleaning up existing environments & builds..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clean python virtual environments
echo "-> Removing Python virtual environments..."
rm -rf .venv .venv-hybrid .venv-piper

# Clean frontend and emulator node_modules and builds
echo "-> Removing frontend and emulator build artifacts..."
rm -rf clients/browser/node_modules clients/browser/dist
rm -rf clients/desktop_robot_emulator/node_modules clients/desktop_robot_emulator/dist

# Clean general caches
echo "-> Cleaning Python caches..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache

echo "✅ Clean up completed!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Phase 2: Installing system prerequisites..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for uv package manager
if ! command -v uv &>/dev/null; then
  echo "-> Installing 'uv' package manager..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add to path for this session
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "-> 'uv' is already installed."
fi

# Check for node and npm
if ! command -v npm &>/dev/null; then
  echo "⚠️ 'npm' is missing. Please install Node.js (v18+) and npm before running this script."
  echo "   On Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y nodejs npm"
  exit 1
fi

# Check for required system packages for audio/STT
echo "-> Checking for system audio libraries (ffmpeg, libgomp1, libsndfile1)..."
echo "📌 Make sure you have installed them on your Linux system:"
echo "   sudo apt-get update && sudo apt-get install -y libgomp1 libsndfile1 ffmpeg lsof"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Phase 3: Building Python environments..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PYTHON_VERSION="3.12"
PIPER_VERSION="1.5.0"
PIPER_VOICE="vi_VN-vais1000-medium"

# 1. Main Virtual Environment
echo "-> Installing Python $PYTHON_VERSION and syncing main environment (.venv)..."
uv python install "$PYTHON_VERSION"
uv sync --frozen --python "$PYTHON_VERSION"

# 2. Hybrid Local Virtual Environment (.venv-hybrid)
echo "-> Creating and configuring hybrid local environment (.venv-hybrid)..."
uv venv .venv-hybrid --python "$PYTHON_VERSION"
uv pip install --python .venv-hybrid/bin/python \
  "pipecat-ai[whisper]==1.6.0" \
  "faster-whisper" \
  "sherpa-onnx" \
  "huggingface-hub" \
  "vieneu" \
  "python-multipart>=0.0.18" \
  "piper-tts>=1.5.0"

# Install CUDA libraries for GPU acceleration if NVIDIA GPU is present
if command -v nvidia-smi &>/dev/null; then
  echo "🟢 NVIDIA GPU detected. Installing CUDA 12 & cuDNN runtime for faster-whisper..."
  uv pip install --python .venv-hybrid/bin/python \
    nvidia-cublas-cu12 \
    nvidia-cudnn-cu12
fi

# 3. Piper TTS Server Environment (.venv-piper)
echo "-> Creating and configuring Piper TTS server environment (.venv-piper)..."
uv venv .venv-piper --python "$PYTHON_VERSION"
uv pip install --python .venv-piper/bin/python "piper-tts[http]==${PIPER_VERSION}"

echo "-> Downloading Piper Voice: $PIPER_VOICE..."
mkdir -p models/piper
.venv-piper/bin/python -m piper.download_voices \
  --data-dir models/piper "$PIPER_VOICE"

echo "✅ Python environments build completed!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Phase 4: Building Web clients..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Build browser client
echo "-> Installing and building browser client..."
npm ci --prefix clients/browser
npm run build --prefix clients/browser

# 2. Build desktop robot emulator
echo "-> Installing and building desktop robot emulator..."
npm ci --prefix clients/desktop_robot_emulator
npm run build --prefix clients/desktop_robot_emulator

echo "✅ Web clients build completed!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Phase 5: Verifying configuration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run hybrid check to ensure all modules load correctly
if .venv-hybrid/bin/python scripts/check_hybrid_profile.py --profile hybrid_local_vi --skip-piper-health; then
  echo "✅ Hybrid environment verification passed!"
else
  echo "❌ Hybrid environment verification failed! Please check logs."
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Reconstruction completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "To start the project, copy .env.example to .env (if not done already) and run:"
echo "   bash start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
