# PROJECT W.A.L.L. - Dual Startup Script (Backend & Frontend)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PROJECT W.A.L.L. - 4-Cable Planar Surface Printer CDPR" -ForegroundColor Cyan
Write-Host "  Autonomous Robotic Digital Twin System Launch" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "1. Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
$backendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; python main.py" -PassThru

Write-Host "2. Launching Web Frontend on http://localhost:3000..." -ForegroundColor Yellow
$frontendJob = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npx --yes http-server . -p 3000 -c-1" -PassThru

Write-Host "`nAll services launched successfully!" -ForegroundColor Green
Write-Host "Open your browser to: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend API docs at:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Direct Unified App:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C in the spawned terminal windows to stop the services." -ForegroundColor DarkGray
