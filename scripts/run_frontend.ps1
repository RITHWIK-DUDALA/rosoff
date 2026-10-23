# Start Standalone Frontend Static Server for CDPR Digital Twin (Windows PowerShell)
$ErrorActionPreference = "Stop"

$Port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $WorkspaceRoot "frontend"

Write-Host "=== Starting CDPR Frontend Static Server ===" -ForegroundColor Cyan
Write-Host "Serving frontend at http://localhost:$Port..." -ForegroundColor Green
Write-Host "Connecting to backend at http://localhost:8000..." -ForegroundColor Yellow

Set-Location $FrontendDir

if (Get-Command npx -ErrorAction SilentlyContinue) {
    npx --yes http-server . -p $Port -c-1
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m http.server $Port
} else {
    Write-Error "Neither npx nor python found in PATH."
}
