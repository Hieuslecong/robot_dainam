#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv-hybrid/bin/python ]]; then
  echo "Missing .venv-hybrid. Run the platform hybrid installer first." >&2
  exit 2
fi

exec .venv-hybrid/bin/python -m app.main --profile hybrid_local_vi "$@"
