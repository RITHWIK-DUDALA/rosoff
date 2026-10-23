#!/usr/bin/env bash
# Start Standalone Frontend Static Server for CDPR Digital Twin
set -e

PORT=${FRONTEND_PORT:-3000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Starting CDPR Frontend Static Server ==="
echo "Serving frontend/ at http://localhost:$PORT..."
echo "Connecting to backend at http://localhost:8000..."

cd "$WORKSPACE_ROOT/frontend"

if command -v npx &> /dev/null; then
    exec npx --yes http-server . -p "$PORT" -c-1
elif command -v python3 &> /dev/null; then
    exec python3 -m http.server "$PORT"
else
    exec python -m http.server "$PORT"
fi
