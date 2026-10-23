# Start ROS 2 CDPR Workspace (PowerShell)
if (-not (Get-Command ros2 -ErrorAction SilentlyContinue)) {
    Write-Host "Notice: ros2 CLI not found in current PATH." -ForegroundColor Yellow
    Write-Host "To run native ROS 2 nodes, source your ROS 2 environment (or run under WSL2 / Ubuntu)."
    Write-Host "The Python backend and Three.js frontend run natively in simulation mode without ROS 2." -ForegroundColor Green
    exit 0
}

Write-Host "=== Building ROS 2 CDPR Workspace ===" -ForegroundColor Cyan
Set-Location ros2_ws
colcon build --symlink-install
. .\install\setup.ps1

Write-Host "Starting ROS 2 CDPR simulation bringup..." -ForegroundColor Green
ros2 launch cdpr_bringup simulation.launch.py
