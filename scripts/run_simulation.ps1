# Start CDPR Digital Twin Simulator Backend and Web UI (PowerShell)
$port = if ($env:PORT) { $env:PORT } else { 8000 }

Write-Host "Starting CDPR Digital Twin Simulator on http://localhost:$port..." -ForegroundColor Cyan
Write-Host "Mode A: Safe Offline Simulation." -ForegroundColor Green

uvicorn backend.main:app --host 0.0.0.0 --port $port --reload
