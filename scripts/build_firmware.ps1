# Build ESP32 micro-ROS Firmware (Windows PowerShell / ESP-IDF Tools)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$FwDir = Join-Path $WorkspaceRoot "firmware" "esp32_micro_ros"

Write-Host "=== Building ESP32 micro-ROS Firmware ===" -ForegroundColor Cyan

if (Get-Command idf.py -ErrorAction SilentlyContinue) {
    Set-Location $FwDir
    Write-Host "Setting target to esp32..." -ForegroundColor Green
    idf.py set-target esp32
    Write-Host "Building firmware..." -ForegroundColor Green
    idf.py build
    Write-Host "Build complete! To flash: idf.py -p COM3 flash monitor" -ForegroundColor Green
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "Executing firmware build inside WSL2 environment..." -ForegroundColor Yellow
    wsl bash -c "cd '$FwDir' && if [ -f ~/esp/esp-idf/export.sh ]; then source ~/esp/esp-idf/export.sh; fi && idf.py set-target esp32 && idf.py build"
} else {
    Write-Host "Notice: ESP-IDF build requires ESP-IDF v5.1+ installed." -ForegroundColor Yellow
    Write-Host "See docs/micro_ros_setup.md for full toolchain setup instructions." -ForegroundColor White
}
