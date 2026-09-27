#!/usr/bin/env bash
# RAMP Operational Startup Script
# SIH26080 | MoES / NCMRWF

export APP_ENV="${APP_ENV:-PRODUCTION}"
export PYTHONPATH=".:backend/src"

echo "Starting RAMP Operational Platform in $APP_ENV mode..."
exec uvicorn ramp.main:app --app-dir backend/src --host 0.0.0.0 --port "${APP_PORT:-8000}" --workers "${WORKERS:-4}"
