#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PIPER_HOST="${PIPER_HOST:-127.0.0.1}"
PIPER_PORT="${PIPER_PORT:-5000}"
PIPER_VOICE="${PIPER_VOICE:-vi_VN-vais1000-medium}"
PIPER_DATA_DIR="${PIPER_DATA_DIR:-models/piper}"

if [[ ! -x .venv-piper/bin/python ]]; then
  echo "Missing .venv-piper. Run scripts/install_hybrid_macos.sh or scripts/install_hybrid_linux.sh first." >&2
  exit 2
fi

exec .venv-piper/bin/python -m piper.http_server \
  --host "$PIPER_HOST" \
  --port "$PIPER_PORT" \
  --data-dir "$PIPER_DATA_DIR" \
  -m "$PIPER_VOICE"
