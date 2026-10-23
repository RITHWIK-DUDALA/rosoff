# Build ROS 2 CDPR Workspace (Windows PowerShell / WSL2 Ubuntu 24.04 Jazzy)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$Ros2Dir = Join-Path $WorkspaceRoot "ros2_ws"

Write-Host "=== Building CDPR ROS 2 Workspace ===" -ForegroundColor Cyan

if (Get-Command colcon -ErrorAction SilentlyContinue) {
    Set-Location $Ros2Dir
    Write-Host "Building packages in $Ros2Dir..." -ForegroundColor Green
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    Write-Host "Build complete! Source install/setup.ps1 or run with ROS 2." -ForegroundColor Green
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "Colcon not found natively on Windows. Executing via WSL..." -ForegroundColor Yellow
    wsl bash -c "cd '$Ros2Dir' && if [ -f /opt/ros/jazzy/setup.bash ]; then source /opt/ros/jazzy/setup.bash; elif [ -f /opt/ros/humble/setup.bash ]; then source /opt/ros/humble/setup.bash; fi && colcon build --symlink-install"
} else {
    Write-Host "Notice: ROS 2 colcon build requires Ubuntu 24.04 LTS with ROS 2 Jazzy (Native or WSL2)." -ForegroundColor Yellow
    Write-Host "See docs/ros2_integration.md for full setup instructions." -ForegroundColor White
}
