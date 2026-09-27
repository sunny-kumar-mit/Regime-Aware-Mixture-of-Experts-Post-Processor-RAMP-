#!/usr/bin/env bash
# RAMP Operational Healthcheck Script
# Usage: ./healthcheck.sh [endpoint]

HOST="${RAMP_HOST:-http://localhost:8000}"
ENDPOINT="${1:-/health/overall}"

STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${HOST}${ENDPOINT}")

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "[OK] ${HOST}${ENDPOINT} returned HTTP 200"
    exit 0
else
    echo "[CRITICAL] ${HOST}${ENDPOINT} returned HTTP ${STATUS_CODE}"
    exit 1
fi
