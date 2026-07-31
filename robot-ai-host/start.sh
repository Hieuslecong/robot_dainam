#!/usr/bin/env bash
# Minimal start script - no set -e, no traps, pure simplicity
cd "$(dirname "$0")"

PROFILE="${DEFAULT_PROFILE:-hybrid_local_vi}"
PORT="${PORT:-8000}"
LOCK_FILE=".server.lock"
TUNNEL_LOG="cflog.$$.log"

# Lock check
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Another instance running (pid $OLD_PID). Stop it first."
        exit 1
    fi
    rm -f "$LOCK_FILE"
fi

echo ""
echo "=== Starting Robot AI Host ==="

# Start tunnel
echo "Starting Cloudflare Quick Tunnel..."
cloudflared tunnel --url http://localhost:$PORT > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# Parse domain
echo "Waiting for tunnel domain (max 60s)..."
TUNNEL_URL=""
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    FOUND=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        TUNNEL_URL="$FOUND"
        export TUNNEL_URL
        echo "Tunnel ready: $TUNNEL_URL"
        break
    fi
    sleep 2
done

if [ -z "$TUNNEL_URL" ]; then
    echo "WARNING: No tunnel domain found, continuing anyway..."
else
    echo "CORS auto-added: $TUNNEL_URL"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sudo -n dscacheutil -flushcache 2>/dev/null || true
        sudo -n killall -HUP mDNSResponder 2>/dev/null || true
    fi
fi

# Start bot
echo ""
echo "Starting bot on port $PORT..."
PYTHONPATH= .venv/bin/python3 -m app.main \
    --profile "$PROFILE" \
    --port "$PORT" \
    --host 0.0.0.0 &
SERVER_PID=$!
echo "$$" > "$LOCK_FILE"

echo "Server PID: $SERVER_PID | Tunnel PID: $TUNNEL_PID"
echo "Dashboard: http://localhost:$PORT/dashboard"
[ -n "$TUNNEL_URL" ] && echo "Public:    $TUNNEL_URL/dashboard"
echo ""

# Wait for any signal
trap "echo 'Received signal, shutting down...'; kill $SERVER_PID $TUNNEL_PID 2>/dev/null; rm -f $LOCK_FILE $TUNNEL_LOG; exit 0" INT TERM
wait
