# Run all automated test suites for CDPR (PowerShell)
Write-Host "=== Running CDPR Automated Tests ===" -ForegroundColor Cyan
pytest -v --durations=10 tests/
