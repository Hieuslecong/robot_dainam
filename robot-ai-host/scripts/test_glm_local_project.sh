#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p artifacts/glm-local-test
LOG_DIR="artifacts/glm-local-test"

if [[ ! -f .env ]]; then
  echo "[FAIL] Missing .env. Run: .venv-hybrid/bin/python scripts/configure_glm_local.py" >&2
  exit 2
fi
if [[ ! -x .venv-hybrid/bin/python ]]; then
  echo "[FAIL] Missing .venv-hybrid. Run the platform Hybrid installer." >&2
  exit 2
fi

{
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "os=$(uname -s)"
  echo "arch=$(uname -m)"
  .venv-hybrid/bin/python --version
  node --version
  npm --version
} | tee "$LOG_DIR/environment.txt"

.venv-hybrid/bin/python scripts/check_llm_endpoint.py \
  | tee "$LOG_DIR/llm-endpoint.txt"

.venv-hybrid/bin/python scripts/check_hybrid_profile.py --profile hybrid_local_vi \
  | tee "$LOG_DIR/hybrid-profile.txt"

.venv-hybrid/bin/python -m pytest -q \
  | tee "$LOG_DIR/python-tests.txt"

npm ci --prefix clients/browser \
  | tee "$LOG_DIR/frontend-install.txt"
npm run test --prefix clients/browser \
  | tee "$LOG_DIR/frontend-tests.txt"
npm run build --prefix clients/browser \
  | tee "$LOG_DIR/frontend-build.txt"

cat <<'EOF'
[AUTOMATED TESTS PASS]
Next manual gate:
  1. Start Piper: ./scripts/run_piper.sh
  2. Start host: ./scripts/run_glm_local_hybrid.sh
  3. Open http://127.0.0.1:8000/client
  4. Run the microphone, speaker, context and barge-in tests in PROMPT_TEST_GLM_LOCAL.md.
EOF
