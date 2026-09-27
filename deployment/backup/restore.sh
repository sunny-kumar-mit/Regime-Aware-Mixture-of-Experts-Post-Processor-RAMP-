#!/usr/bin/env bash
# RAMP Backup Restoration & Checksum Verification Script
# Usage: ./restore.sh <manifest_path>
set -e

MANIFEST="${1}"
if [ -z "$MANIFEST" ]; then
    echo "Usage: ./restore.sh <path_to_manifest.json>"
    exit 1
fi

python -c "
import sys
from pathlib import Path
from ml.production.backup import ProductionBackupManager

p = Path(sys.argv[1])
if ProductionBackupManager.verify_backup(p):
    print(f'[OK] Backup manifest {p} is cryptographically verified.')
else:
    print(f'[FAIL] Backup checksum mismatch or archive missing for {p}!')
    sys.exit(1)
" "$MANIFEST"
