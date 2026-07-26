#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Missing .env. Run: .venv-hybrid/bin/python scripts/configure_glm_local.py" >&2
  exit 2
fi
if [[ ! -x .venv-hybrid/bin/python ]]; then
  echo "Missing .venv-hybrid. Run the platform hybrid installer first." >&2
  exit 2
fi

.venv-hybrid/bin/python scripts/check_llm_endpoint.py
.venv-hybrid/bin/python scripts/check_hybrid_profile.py --profile hybrid_local_vi
exec .venv-hybrid/bin/python -m app.main --profile hybrid_local_vi "$@"
