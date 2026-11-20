#!/usr/bin/env bash
# Production: build the frontend, then serve everything from FastAPI on one port.
# Phones on the same Wi-Fi can open http://<this-pc-lan-ip>:8000
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"

VENV="$ROOT/backend/venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv "$VENV"
fi
echo "==> Installing backend dependencies"
# torch from the CPU index: the default PyPI wheel drags in ~2.5 GB of CUDA.
"$VENV/bin/pip" install -q --index-url https://download.pytorch.org/whl/cpu torch torchvision
"$VENV/bin/pip" install -q -r backend/requirements.txt

echo "==> Checking vision model weights (first run downloads ~1 GB)"
"$VENV/bin/python" backend/scripts/fetch_models.py

echo "==> Building frontend"
(cd frontend && npm install --silent && npm run build)

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "  local   : http://localhost:8000"
[ -n "${LAN_IP:-}" ] && echo "  on Wi-Fi: http://$LAN_IP:8000"
echo

cd backend
exec "$VENV/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
