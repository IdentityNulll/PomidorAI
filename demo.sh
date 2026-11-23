#!/usr/bin/env bash
# One command for a live demo: backend + public HTTPS tunnel + a QR code for
# the judges to scan. Works on any phone on any network, including cellular.
#
#   ./demo.sh
#
# The tunnel serves the WHOLE app - FastAPI hosts the frontend and the API on
# the same port - so there is no CORS or cross-site cookie setup to get wrong.
# Leave this terminal open; Ctrl+C stops everything it started.
#
# The URL is random and changes every run, so make the QR on the day.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"

VENV="$ROOT/backend/venv"
CLOUDFLARED="${CLOUDFLARED:-$HOME/.local/bin/cloudflared}"
LOG_DIR="$ROOT/backend/data/demo"
mkdir -p "$LOG_DIR"
TUNNEL_LOG="$LOG_DIR/tunnel.log"
SERVER_LOG="$LOG_DIR/server.log"

if [ ! -x "$CLOUDFLARED" ] && ! command -v cloudflared >/dev/null 2>&1; then
  cat <<'MSG'
cloudflared is not installed. Install it once with:

  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o ~/.local/bin/cloudflared && chmod +x ~/.local/bin/cloudflared
MSG
  exit 1
fi
command -v cloudflared >/dev/null 2>&1 && CLOUDFLARED="$(command -v cloudflared)"

SERVER_PID=""
TUNNEL_PID=""
cleanup() {
  echo
  echo "==> Stopping"
  [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
  # Only stop the server if this script started it.
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Reuse a server that is already running, so this can be started alongside an
# existing ./start.sh without fighting over port 8000.
if curl -sf --max-time 3 http://localhost:8000/api/health >/dev/null 2>&1; then
  echo "==> Using the backend already running on :8000"
else
  echo "==> Starting the backend (first run builds the frontend, ~1 min)"
  ./start.sh > "$SERVER_LOG" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 120); do
    curl -sf --max-time 3 http://localhost:8000/api/health >/dev/null 2>&1 && break
    sleep 2
  done
  if ! curl -sf --max-time 3 http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "Backend did not come up. Last lines of $SERVER_LOG:"
    tail -20 "$SERVER_LOG"
    exit 1
  fi
fi
echo "    backend ready"

echo "==> Opening the public tunnel"
rm -f "$TUNNEL_LOG"
"$CLOUDFLARED" tunnel --url http://localhost:8000 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

URL=""
for _ in $(seq 1 60); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 2
done
if [ -z "$URL" ]; then
  echo "Tunnel did not produce a URL. Last lines of $TUNNEL_LOG:"
  tail -20 "$TUNNEL_LOG"
  exit 1
fi

# Confirm the tunnel actually reaches the app before handing out a QR code.
echo "==> Checking the public URL"
for _ in $(seq 1 20); do
  curl -sf --max-time 15 "$URL/api/health" >/dev/null 2>&1 && break
  sleep 3
done
if ! curl -sf --max-time 15 "$URL/api/health" >/dev/null 2>&1; then
  echo "The tunnel is up but $URL is not answering yet. Try again in a moment."
  exit 1
fi

"$VENV/bin/python" -c "import qrcode" 2>/dev/null || {
  echo "==> Installing the QR dependency"
  "$VENV/bin/pip" install -q "qrcode[pil]"
}
QR_OUT="$HOME/Documents/pomidorai-qr/pomidorai-qr.png"
"$VENV/bin/python" backend/scripts/make_qr.py "$URL" "$QR_OUT" >/dev/null

cat <<MSG

  ============================================================
    PomidorAI is live

    $URL

    QR code : $QR_OUT
    On Wi-Fi: http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000
  ============================================================

  Scan the QR with a phone camera. Works on mobile data too.
  Keep this terminal open. Ctrl+C stops everything.

MSG

command -v xdg-open >/dev/null 2>&1 && xdg-open "$QR_OUT" >/dev/null 2>&1 || true

wait
