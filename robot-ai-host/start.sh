#!/usr/bin/env bash
set -euo pipefail
# ── Start robot-ai-host server + cloudflared tunnel ─────────────────────

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
VENV=".venv-hybrid"

SERVER_PID=""
TUNNEL_PID=""
TUNNEL_LOG=$(mktemp -t cflog.XXXXXX)
DONE=false

cleanup() {
    $DONE && return
    DONE=true
    echo ""
    echo "🛑 Stopping..."
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
    [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null
    lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null
    rm -f "$TUNNEL_LOG"
    echo "✅ Stopped."
}
trap cleanup EXIT INT TERM

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Robot AI Host + Cloudflare"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Clean old server (don't touch other cloudflared) ─────────────────
echo "🧹 Cleaning..."
pkill -f "app.main --profile" 2>/dev/null || true
lsof -ti :8000 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# ── 2. Start server ────────────────────────────────────────────────────
echo "📡 Starting server..."
PYTHONPATH=. "$VENV/bin/python" -m app.main --profile hybrid_local_vi >/dev/null 2>&1 &
SERVER_PID=$!

for i in $(seq 1 20); do
    curl -sk --max-time 2 "https://127.0.0.1:8000/health" >/dev/null 2>&1 && break
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "❌ Server crashed"; exit 1; }
    sleep 1
done
echo "   ✅ Server ready (port 8000)"

# ── 3. Start tunnel with retry ─────────────────────────────────────────
start_tunnel() {
    >"$TUNNEL_LOG"
    cloudflared tunnel --url https://localhost:8000 --no-tls-verify --protocol http2 >"$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!
}

wait_for_url() {
    for i in $(seq 1 30); do
        URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
        [ -n "$URL" ] && { echo "$URL"; return 0; }
        if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then return 1; fi
        sleep 1
    done
    return 1
}

TUNNEL_URL=""
for attempt in 1 2 3; do
    echo "🌐 Starting tunnel (attempt $attempt)..."
    start_tunnel
    TUNNEL_URL=$(wait_for_url) && break
    echo "   ⚠️  Tunnel failed, retrying..."
    kill "$TUNNEL_PID" 2>/dev/null || true
    sleep 2
done

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Tunnel failed after 3 attempts"
    exit 1
fi

# Verify
if curl -sk --max-time 5 "$TUNNEL_URL/health" >/dev/null 2>&1; then
    echo "   ✅ $TUNNEL_URL"
else
    echo "   ⚠️  $TUNNEL_URL (DNS may need a moment)"
fi

# ── 4. Keep tunnel alive ───────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Ready!  (tunnel auto-restarts if dropped)"
echo ""
echo "  Public:  ${TUNNEL_URL}/client/"
echo ""
echo "  Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Monitor loop — restart tunnel if it dies
while true; do
    wait "$TUNNEL_PID" 2>/dev/null || true
    echo "🔄 Tunnel lost, restarting..."
    sleep 3
    start_tunnel
    TUNNEL_URL=$(wait_for_url)
    if [ -n "$TUNNEL_URL" ]; then
        echo "   ✅ $TUNNEL_URL"
    fi
done
