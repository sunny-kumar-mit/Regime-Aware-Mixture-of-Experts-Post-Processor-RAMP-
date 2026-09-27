#!/usr/bin/env bash
# RAMP Production Deployment Script
# SIH26080 | MoES / NCMRWF
set -e

echo "=== Deploying RAMP Operational Platform ==="

# 1. Validate configuration
echo "[1/4] Validating production configuration..."
python -c "from ml.production.config import get_production_config, ProductionConfigValidator; cfg = get_production_config(); ProductionConfigValidator.validate_config(cfg); print('[OK] Configuration valid.')"

# 2. Build frontend if needed
echo "[2/4] Verifying frontend assets..."
if [ -d "frontend/dist" ]; then
    echo "[OK] Frontend dist directory present."
else
    echo "Building frontend bundle..."
    cd frontend && npm run build && cd ..
fi

# 3. Check data directories
echo "[3/4] Ensuring operational directory skeleton..."
mkdir -p data/ncmrwf data/imd data/processed/forecasts data/audit data/logs data/backups

# 4. Verify model registry
echo "[4/4] Verifying model registry..."
python -c "from pathlib import Path; assert Path('ml/model_registry').exists(); print('[OK] Model registry present.')"

echo "=== Deployment Pre-flight Checks Passed ==="
