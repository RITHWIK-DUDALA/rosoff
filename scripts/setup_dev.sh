#!/usr/bin/env bash
# CDPR Development Environment Setup Script for Ubuntu 24.04 (Noble) & Ubuntu 22.04 (Jammy)
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

# On Ubuntu 24.04 (Python 3.12+), PEP 668 restricts global pip install.
# We create or activate a virtualenv with --system-site-packages so ROS 2 rclpy is visible.
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment (.venv) with system site packages (for ROS 2)..."
        $PY_CMD -m venv --system-site-packages .venv
    fi
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
    PY_CMD=python
fi

echo "Installing Python backend and development dependencies..."
$PY_CMD -m pip install --upgrade pip
$PY_CMD -m pip install -r backend/requirements.txt

if [ -f frontend/package.json ] && command -v npm &> /dev/null; then
    echo "Auditing frontend package..."
    (cd frontend && npm install --package-lock-only)
fi

echo "Validating canonical robot configuration..."
$PY_CMD -c "from backend.cdpr.config import load_robot_config; cfg = load_robot_config(); print('Loaded config successfully. Robot ID:', cfg.robot_id, '| Schema:', cfg.schema_version)"

echo ""
echo "=== Setup complete! ==="
echo "To run simulation: ./scripts/run_simulation.sh"
echo "To run tests:      ./scripts/run_tests.sh"
