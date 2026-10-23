#!/usr/bin/env bash
# Start ROS 2 CDPR Workspace
set -e

if ! command -v ros2 &> /dev/null; then
  echo "Error: ros2 CLI not found in PATH."
  echo "Please source your ROS 2 environment (e.g. source /opt/ros/humble/setup.bash) first."
  exit 1
fi

echo "=== Building ROS 2 CDPR Workspace ==="
cd ros2_ws
colcon build --symlink-install
source install/setup.bash

echo "Starting ROS 2 CDPR simulation bringup..."
ros2 launch cdpr_bringup simulation.launch.py
