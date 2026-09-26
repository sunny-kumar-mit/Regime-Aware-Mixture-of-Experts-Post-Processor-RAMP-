#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting RAMP (SIH26080) Local Development Environment"
echo "=========================================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Start backend in background
echo "Starting FastAPI backend on http://localhost:8000..."
(
    cd "$ROOT_DIR/backend"
    export PYTHONPATH="src"
    python -m uvicorn ramp.main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

# Trap termination to kill backend process
trap "kill $BACKEND_PID" EXIT INT TERM

# Start frontend
echo "Starting Vite frontend on http://localhost:5173..."
cd "$ROOT_DIR/frontend"
npm run dev
