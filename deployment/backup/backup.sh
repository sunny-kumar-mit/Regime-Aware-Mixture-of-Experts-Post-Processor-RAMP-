#!/usr/bin/env bash
# RAMP Automated Backup Script
# SIH26080 | MoES / NCMRWF
set -e

BACKUP_DIR="${RAMP_BACKUP_DIR:-data/backups}"
mkdir -p "$BACKUP_DIR"

python -c "from ml.production.backup import ProductionBackupManager; m = ProductionBackupManager.create_backup('OPERATIONAL_CLI'); print('Created backup:', m.backup_id)"
