#!/usr/bin/env bash
# RAMP Emergency Stop Script
# Usage: ./emergency_stop.sh "<reason>"
set -e

REASON="${1:-Emergency stop commanded via operational console}"
ACTOR="${OPERATOR_ID:-ADMIN_CLI}"

python -c "
import sys
from ml.production.emergency import EmergencyShutdownManager
from ml.production.audit import UserRole

mgr = EmergencyShutdownManager()
st = mgr.trigger_emergency_stop(actor='$ACTOR', role=UserRole.ADMIN, reason='$REASON')
print('=== EMERGENCY STOP ENGAGED ===')
print('Triggered by:', st.triggered_by)
print('Reason:', st.reason)
print('Timestamp:', st.triggered_at)
"
