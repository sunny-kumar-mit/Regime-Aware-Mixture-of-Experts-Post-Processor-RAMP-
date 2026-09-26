#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Running Backend Tests..."
export PYTHONPATH="$ROOT_DIR/backend/src"
python -m pytest "$ROOT_DIR/backend/tests" "$ROOT_DIR/tests"

echo "Running Frontend Type Checks..."
cd "$ROOT_DIR/frontend"
npm run lint

echo "All tests and type checks passed successfully!"
