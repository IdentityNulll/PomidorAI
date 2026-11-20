#!/usr/bin/env bash
# Development: FastAPI with reload on :8000, Vite dev server on :5173.
# Open http://localhost:5173 - it proxies /api to the backend.
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

if [ ! -d frontend/node_modules ]; then
  echo "==> Installing frontend dependencies"
  (cd frontend && npm install)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd backend && "$VENV/bin/python" -m uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &

echo
echo "  backend : http://localhost:8000"
echo "  frontend: http://localhost:5173   <- open this one"
echo
wait
