#!/usr/bin/env bash
# CDPR Diagnostics and Health Check Script (Ubuntu Linux)
set -e

PORT=${PORT:-8000}
URL="http://localhost:$PORT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== CDPR Health and Diagnostics Inspection ==="
cd "$WORKSPACE_ROOT"

if command -v python3 &> /dev/null; then
    PY_CMD=python3
else
    PY_CMD=python
fi

echo "[1] Python Environment:"
$PY_CMD --version

echo "[2] Configuration & JSON Schema Validation:"
$PY_CMD -c "from backend.cdpr.config import load_robot_config; cfg = load_robot_config(); print('    Valid configuration loaded: Robot ID =', cfg.robot_id, '| Schema =', cfg.schema_version)"

echo "[3] Active Port $PORT Status:"
if curl -s "$URL/api/health" &> /dev/null; then
    echo "    Backend running! Health response:"
    curl -s "$URL/api/health"
    echo ""
    echo "    Hardware Verification Profile:"
    curl -s "$URL/api/hardware/profile"
    echo ""
else
    echo "    Backend is currently offline (port $PORT). Run ./scripts/run_simulation.sh to start."
fi
