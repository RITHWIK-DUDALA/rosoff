#!/usr/bin/env bash
# Run all automated test suites for CDPR on Ubuntu Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running CDPR Automated Tests ==="
cd "$WORKSPACE_ROOT"

if command -v pytest &> /dev/null; then
    exec pytest -v --durations=10 tests/
elif command -v python3 &> /dev/null; then
    exec python3 -m pytest -v --durations=10 tests/
else
    exec python -m pytest -v --durations=10 tests/
fi
