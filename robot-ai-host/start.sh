#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PROFILE="${DEFAULT_PROFILE:-hybrid_local_vi}"
PORT="${PORT:-8765}"
LOCK_FILE=".server.lock"

SERVER_PID=""
TUNNEL_PID=""

export HF_HUB_DISABLE_IMPLICIT_TOKEN_WARNING=1
export HF_HUB_DISABLE_SYMLINKS_WARNING=1


cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
  rm -f "$LOCK_FILE"
  exit 0
}
trap cleanup INT TERM EXIT

if [ -f "$LOCK_FILE" ]; then
  LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || true)
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    echo "❌ Another instance is running (pid $LOCK_PID). Stop it first."
    exit 1
  else
    rm -f "$LOCK_FILE"
  fi
fi

echo $$ > "$LOCK_FILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Cleaning..."
pkill -f "cloudflared tunnel" 2>/dev/null || true
# Kill any zombie process still holding port 8000
OLD_PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
  echo "   ⚠️  Killing stale process on port $PORT (PID: $OLD_PID)..."
  kill -9 $OLD_PID 2>/dev/null || true
  sleep 1
fi

# ── Start server first ──
mkdir -p logs
rm -f logs/tunnel_url.txt
echo "📡 Starting server (profile=$PROFILE, port=$PORT)..."
.venv/bin/python -m app.main --profile "$PROFILE" --port "$PORT" >> logs/server.log 2>&1 &
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
  echo "$(date) [INFO] Tunnel attempt $TUNNEL_ATTEMPT..." >> logs/server.log
  cloudflared tunnel --url "https://localhost:$PORT" --no-tls-verify --protocol http2 2>&1 | while IFS= read -r line; do
    echo "$line" >> logs/server.log
    # Extract tunnel URL and save to logs/tunnel_url.txt
    TURL=$(echo "$line" | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1 || true)
    if [ -n "$TURL" ]; then
      echo "$TURL" > logs/tunnel_url.txt
      echo "$(date) [INFO] Public Tunnel URL created: $TURL" >> logs/server.log
      echo "   ✅ Public Tunnel URL: $TURL"
    fi
  done
  TUNNEL_ATTEMPT=$((TUNNEL_ATTEMPT + 1))
  echo "$(date) [WARN] Tunnel dropped, restarting in 3s..." >> logs/server.log
  sleep 3
done &
TUNNEL_PID=$!


echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Ready!"
echo ""
echo "   Health:    https://127.0.0.1:$PORT/health"
echo "   Robot:     https://127.0.0.1:$PORT/robot/"
echo "   Dashboard: https://127.0.0.1:$PORT/dashboard"
echo "   API Admin: https://127.0.0.1:$PORT/v1/admin/settings"
echo ""
echo "   Model:  $(grep LLM_MODEL .env 2>/dev/null | cut -d= -f2)"
echo "   Profile: $PROFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Press Ctrl+C to stop"

wait "$SERVER_PID"

