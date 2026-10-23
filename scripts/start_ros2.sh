#!/usr/bin/env bash
# Start ROS 2 CDPR Workspace on Ubuntu 24.04 (ROS 2 Jazzy) / Ubuntu 22.04 (ROS 2 Humble)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS2_DIR="$WORKSPACE_ROOT/ros2_ws"

if ! command -v ros2 &> /dev/null; then
    if [ -f /opt/ros/jazzy/setup.bash ]; then
        echo "Auto-sourcing ROS 2 Jazzy (/opt/ros/jazzy/setup.bash)..."
        source /opt/ros/jazzy/setup.bash
    elif [ -f /opt/ros/humble/setup.bash ]; then
        echo "Auto-sourcing ROS 2 Humble (/opt/ros/humble/setup.bash)..."
        source /opt/ros/humble/setup.bash
    else
        echo "Error: ros2 CLI not found in PATH."
        echo "Please install ROS 2 Jazzy (Ubuntu 24.04) or source your environment:"
        echo "  source /opt/ros/jazzy/setup.bash"
        exit 1
    fi
fi

echo "=== Building ROS 2 CDPR Workspace ==="
cd "$ROS2_DIR"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash

echo "Starting ROS 2 CDPR simulation bringup..."
ros2 launch cdpr_bringup simulation.launch.py
