# Launch PROJECT W.A.L.L. Frontend
$frontendDir = Join-Path $PSScriptRoot "..\..\frontend"
Set-Location $frontendDir
Write-Host "Starting PROJECT W.A.L.L. Frontend on http://localhost:3000..." -ForegroundColor Green
npx --yes http-server . -p 3000 -c-1

