#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PROFILE="${DEFAULT_PROFILE:-hybrid_local_vi}"
PORT="${PORT:-8000}"
LOCK_FILE=".server.lock"

cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  kill "$SERVER_PID" 2>/dev/null || true
  kill "$TUNNEL_PID" 2>/dev/null || true
  rm -f "$LOCK_FILE"
  exit 0
}
trap cleanup INT TERM EXIT

if [ -f "$LOCK_FILE" ]; then
  echo "❌ Another instance is running (pid $(cat $LOCK_FILE)). Stop it first."
  exit 1
fi
echo $$ > "$LOCK_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Cleaning..."
pkill -f "cloudflared tunnel" 2>/dev/null || true

# ── Start server first ──
echo "📡 Starting server (profile=$PROFILE, port=$PORT)..."
PYTHONPATH=. ".venv-hybrid/bin/python" -m app.main --profile "$PROFILE" --port "$PORT" &
SERVER_PID=$!

# Wait for server
for i in $(seq 1 15); do
  if curl -sk "https://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "   ✅ Server ready"
    break
  fi
  sleep 1
done

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "❌ Server failed to start"
  exit 1
fi

# ── Start tunnel (with auto-restart on drop) ──
echo "🌐 Starting tunnel..."
TUNNEL_ATTEMPT=1
while true; do
  echo "   Tunnel attempt $TUNNEL_ATTEMPT..."
  cloudflared tunnel --url "https://localhost:$PORT" --no-tls-verify --protocol http2 2>&1 | while IFS= read -r line; do
    echo "$line"
    # Extract tunnel URL and export for CORS auto-discovery
    TURL=$(echo "$line" | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1 || true)
    if [ -n "$TURL" ]; then
      export TUNNEL_URL="$TURL"
      # Restart server to pick up new CORS origin
      if kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        sleep 1
        PYTHONPATH=. ".venv-hybrid/bin/python" -m app.main --profile "$PROFILE" --port "$PORT" &
        SERVER_PID=$!
        echo "   ✅ CORS: auto-added $TURL"
      fi
    fi
  done
  TUNNEL_ATTEMPT=$((TUNNEL_ATTEMPT + 1))
  echo "   🔄 Tunnel dropped, restarting in 3s..."
  sleep 3
done &
TUNNEL_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Ready!"
echo ""
echo "   Health:    https://127.0.0.1:$PORT/health"
echo "   Robot:     https://127.0.0.1:$PORT/robot/"
echo "   Dashboard: https://127.0.0.1:$PORT/v1/admin/"
echo "   CORS:      auto-adds tunnel domain on connect"
echo ""
echo "   Model:  $(grep LLM_MODEL .env 2>/dev/null | cut -d= -f2)"
echo "   Profile: $PROFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Press Ctrl+C to stop"

wait "$SERVER_PID"
