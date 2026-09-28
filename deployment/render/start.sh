#!/bin/bash
set -e

echo "========================================"
echo " RAMP Render Production Startup"
echo " SIH26080 | MoES / NCMRWF"
echo "========================================"
echo "Environment: ${APP_ENV:-production}"
echo "Data mode: ${RAMP_DATA_MODE:-SYNTHETIC_DEMO}"
echo "Render Port: ${PORT:-8080}"
echo "FastAPI Internal Port: 8000"
echo "========================================"

# Prepare runtime writable directories (Render ephemeral filesystem)
mkdir -p /app/data/raw \
         /app/data/interim \
         /app/data/processed \
         /app/data/cache \
         /app/data/audit \
         /app/data/real/vault/objects \
         /app/data/models/regime

# Ensure audit files exist so services can read/write without crashing
touch /app/data/audit/cutover_state.json 2>/dev/null || true
touch /app/data/audit/emergency_status.json 2>/dev/null || true

# Configure Nginx port from Render's dynamic $PORT
export PORT="${PORT:-8080}"
echo "Configuring Nginx reverse proxy to listen on port ${PORT}..."
envsubst '${PORT}' < /etc/nginx/conf.d/ramp.conf.template > /etc/nginx/conf.d/default.conf

# Start FastAPI backend in background on internal loopback (port 8000)
echo "Starting FastAPI backend via Uvicorn..."
export PYTHONPATH="/app:/app/backend/src"
uvicorn ramp.main:app \
    --app-dir /app/backend/src \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --no-access-log &
UVICORN_PID=$!

# Trap signals for graceful shutdown
cleanup() {
    echo "Shutting down RAMP services..."
    kill -TERM "$UVICORN_PID" 2>/dev/null || true
    kill -TERM "$NGINX_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
    wait "$NGINX_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Wait for FastAPI to become ready before routing public traffic
echo "Waiting for FastAPI backend to respond on http://127.0.0.1:8000/health/live..."
READY=0
for i in $(seq 1 45); do
    if curl -s -f http://127.0.0.1:8000/health/live > /dev/null 2>&1; then
        echo "FastAPI backend is ready (attempt $i)!"
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "WARNING: FastAPI backend did not respond within 45s. Starting Nginx anyway..."
fi

# Start Nginx in background
echo "Starting Nginx reverse proxy on port ${PORT}..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "========================================"
echo " RAMP System is fully active on Render!"
echo " Public Port: ${PORT}"
echo " Health Check: /health/live"
echo "========================================"

# Wait for either process to terminate; if either exits, shut down cleanly
wait -n "$UVICORN_PID" "$NGINX_PID"
EXIT_CODE=$?
echo "A core process terminated with code ${EXIT_CODE}. Shutting down..."
cleanup
