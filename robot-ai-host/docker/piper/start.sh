#!/usr/bin/env sh
set -eu
VOICE="${PIPER_VOICE:-vi_VN-vais1000-medium}"
DATA_DIR="${PIPER_DATA_DIR:-/models}"
mkdir -p "$DATA_DIR"
python -m piper.download_voices --data-dir "$DATA_DIR" "$VOICE"
exec python -m piper.http_server \
  --host 0.0.0.0 \
  --port 5000 \
  --data-dir "$DATA_DIR" \
  -m "$VOICE"
