# Launch PROJECT W.A.L.L. FastAPI Backend
$backendDir = Join-Path $PSScriptRoot "..\..\backend"
Set-Location $backendDir
Write-Host "Starting PROJECT W.A.L.L. CDPR Backend on http://localhost:8000..." -ForegroundColor Cyan
python main.py

