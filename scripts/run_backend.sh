#!/usr/bin/env bash
# Start CDPR Python Backend Server
set -e

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Starting CDPR Python Backend Server ==="
echo "Serving REST API and WebSocket at http://$HOST:$PORT..."
echo "Mode A: Safe Offline Simulation."

cd "$WORKSPACE_ROOT"

if command -v python3 &> /dev/null; then
    exec python3 -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
else
    exec python -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
fi
