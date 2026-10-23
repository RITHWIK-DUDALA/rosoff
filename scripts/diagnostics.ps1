# CDPR Diagnostics and Health Check Script (PowerShell)
$port = if ($env:PORT) { $env:PORT } else { 8000 }
$url = "http://localhost:$port"

Write-Host "=== CDPR Health and Diagnostics Inspection ===" -ForegroundColor Cyan
Write-Host "Querying backend at $url..."

try {
    $health = Invoke-RestMethod -Uri "$url/api/health" -Method Get
    Write-Host "Health Status:" -ForegroundColor Green
    $health | ConvertTo-Json
    
    Write-Host "`n--- Hardware Verification Profile ---" -ForegroundColor Yellow
    $hw = Invoke-RestMethod -Uri "$url/api/hardware/profile" -Method Get
    $hw | ConvertTo-Json
} catch {
    Write-Host "Backend is not currently running on port $port." -ForegroundColor Red
}
