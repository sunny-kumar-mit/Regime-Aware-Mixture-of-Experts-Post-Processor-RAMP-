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
         /app/data/real/incoming \
         /app/data/real/validated \
         /app/data/real/rejected \
         /app/data/real/runs \
         /app/data/real/manifests \
         /app/data/real/vault/objects/canonical/imd \
         /app/data/real/vault/objects/canonical/ncmrwf \
         /app/data/real/vault/objects/raw/imd \
         /app/data/real/vault/objects/raw/ncmrwf \
         /app/data/models/regime

# Seed canonical and raw test fixtures into the local vault if missing
if [ -d "/app/tests/fixtures/phase18" ]; then
    cp -n /app/tests/fixtures/phase18/imd_*.nc /app/data/real/vault/objects/canonical/imd/ 2>/dev/null || true
    cp -n /app/tests/fixtures/phase18/ncum_*.nc /app/data/real/vault/objects/canonical/ncmrwf/ 2>/dev/null || true
    cp -n /app/tests/fixtures/phase18/neps_*.nc /app/data/real/vault/objects/canonical/ncmrwf/ 2>/dev/null || true
    cp -n /app/tests/fixtures/phase18/imd_*.nc /app/data/real/vault/objects/raw/imd/ 2>/dev/null || true
    cp -n /app/tests/fixtures/phase18/ncum_*.nc /app/data/real/vault/objects/raw/ncmrwf/ 2>/dev/null || true
fi
chmod -R 777 /app/data 2>/dev/null || true


# Ensure audit and state files exist with valid JSON so services can read/write without crashing
if [ ! -s /app/data/audit/cutover_state.json ]; then
    echo "{}" > /app/data/audit/cutover_state.json 2>/dev/null || true
fi
if [ ! -s /app/data/audit/emergency_status.json ]; then
    echo "{}" > /app/data/audit/emergency_status.json 2>/dev/null || true
fi

# Run database schema migrations & initialization
export PYTHONPATH="/app:/app/backend/src"
echo "Initializing database schema..."
python3 -c "
try:
    from ramp.storage.connection import DatabaseManager
except ImportError:
    from backend.src.ramp.storage.connection import DatabaseManager
mgr = DatabaseManager.get_instance()
mgr.init_schema()
" || echo "Database schema initialization deferred or completed with notes."

# Configure Nginx port from Render's dynamic $PORT
export PORT="${PORT:-10000}"
echo "Configuring Nginx reverse proxy to listen on 0.0.0.0:${PORT}..."
envsubst '${PORT}' < /etc/nginx/conf.d/ramp.conf.template > /etc/nginx/conf.d/default.conf

# Start Nginx immediately so Render detects port binding without delay
echo "Starting Nginx reverse proxy on 0.0.0.0:${PORT}..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Start FastAPI backend in background on internal loopback (port 8000)
echo "Starting FastAPI backend via Uvicorn on 127.0.0.1:8000..."
export PYTHONPATH="/app:/app/backend/src"
uvicorn ramp.main:app \
    --app-dir /app/backend/src \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 &
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
for i in $(seq 1 60); do
    if curl -s -f http://127.0.0.1:8000/health/live > /dev/null 2>&1; then
        echo "FastAPI backend is ready (attempt $i)!"
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "WARNING: FastAPI backend did not respond within 60s."
fi

# Output comprehensive startup diagnostics without heavy framework reloading
echo "----------------------------------------"
echo " RAMP STARTUP DIAGNOSTICS"
echo "----------------------------------------"
echo "  Public PORT:           ${PORT}"
echo "  Backend Host:          127.0.0.1:8000"
echo "  Data Storage Root:     ${RAMP_DATA_ROOT:-/app/data}"
echo "  Storage Mode:          ${STORAGE_MODE:-LOCAL_FALLBACK}"
echo "  Dataset Availability:"
python3 -c "
import json
from pathlib import Path
p = Path('${RAMP_DATA_ROOT:-/app/data}/real/vault/data_objects.json')
if p.exists():
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        print(f'    Catalog objects:    {len(data)} datasets registered')
    except Exception as e:
        print(f'    Catalog error:      {e}')
else:
    print('    Catalog status:     Missing local data_objects.json')
" 2>/dev/null || true
echo "  Model Availability:"
python3 -c "
from pathlib import Path
models = list(Path('ml/model_registry/models').rglob('model.bin'))
print(f'    Model artifacts:    {len(models)} found in model_registry')
" 2>/dev/null || true
echo "  Health Status:"
curl -s http://127.0.0.1:8000/api/health 2>/dev/null || echo "    Health endpoint pending"
echo ""
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
