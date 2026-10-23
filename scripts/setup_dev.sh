#!/usr/bin/env bash
# CDPR Development Environment Setup Script for Ubuntu Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== CDPR Development Environment Setup (Ubuntu Linux) ==="
cd "$WORKSPACE_ROOT"

# Check Python version
if command -v python3 &> /dev/null; then
    PY_CMD=python3
else
    PY_CMD=python
fi

echo "Using Python: $($PY_CMD --version)"
echo "Installing Python backend and development dependencies..."
$PY_CMD -m pip install --upgrade pip
$PY_CMD -m pip install -r backend/requirements.txt

if [ -f frontend/package.json ] && command -v npm &> /dev/null; then
    echo "Auditing frontend package..."
    (cd frontend && npm install --package-lock-only)
fi

echo "Validating configuration..."
$PY_CMD -c "from backend.cdpr.config import load_robot_config; cfg = load_robot_config(); print('Loaded config successfully. Robot ID:', cfg.robot_id)"

echo ""
echo "=== Setup complete! ==="
echo "To run simulation: ./scripts/run_simulation.sh"
echo "To run tests:      ./scripts/run_tests.sh"
