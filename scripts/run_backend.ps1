# Start CDPR Python Backend Server (Windows PowerShell)
$ErrorActionPreference = "Stop"

$Port = if ($env:PORT) { $env:PORT } else { "8000" }
$HostAddr = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir

Write-Host "=== Starting CDPR Python Backend Server ===" -ForegroundColor Cyan
Write-Host "Serving REST API and WebSocket at http://$HostAddr`:$Port..." -ForegroundColor Green
Write-Host "Mode A: Safe Offline Simulation." -ForegroundColor Yellow

Set-Location $WorkspaceRoot
python -m uvicorn backend.main:app --host $HostAddr --port $Port --reload
