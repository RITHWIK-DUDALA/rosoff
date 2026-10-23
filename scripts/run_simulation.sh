#!/usr/bin/env bash
# Start CDPR Digital Twin Simulator Backend and Web UI
set -e

PORT=${PORT:-8000}
echo "Starting CDPR Digital Twin Simulator on http://localhost:$PORT..."
echo "Mode A: Safe Offline Simulation."

exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT --reload
