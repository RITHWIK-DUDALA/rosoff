# Run ROS 2 CDPR Simulation (Windows PowerShell / WSL2 Ubuntu 24.04 Jazzy)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$Ros2Dir = Join-Path $WorkspaceRoot "ros2_ws"

Write-Host "=== Starting CDPR ROS 2 Simulation ===" -ForegroundColor Cyan

if (Get-Command ros2 -ErrorAction SilentlyContinue) {
    Set-Location $Ros2Dir
    ros2 launch cdpr_bringup simulation.launch.py
} elseif (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host "Executing ROS 2 simulation inside WSL2 environment..." -ForegroundColor Yellow
    wsl bash -c "cd '$Ros2Dir' && if [ -f /opt/ros/jazzy/setup.bash ]; then source /opt/ros/jazzy/setup.bash; elif [ -f /opt/ros/humble/setup.bash ]; then source /opt/ros/humble/setup.bash; fi && if [ -f install/setup.bash ]; then source install/setup.bash; fi && ros2 launch cdpr_bringup simulation.launch.py"
} else {
    Write-Host "Notice: ROS 2 runtime requires Ubuntu 24.04 LTS with ROS 2 Jazzy (Native or WSL2)." -ForegroundColor Yellow
    Write-Host "For safe offline simulation without ROS 2, use .\scripts\run_simulation.ps1" -ForegroundColor Green
}
