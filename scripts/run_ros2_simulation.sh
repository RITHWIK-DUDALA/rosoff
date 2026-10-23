#!/usr/bin/env bash
# Run ROS 2 CDPR Simulation on Ubuntu Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS2_DIR="$WORKSPACE_ROOT/ros2_ws"

echo "=== Starting CDPR ROS 2 Simulation ==="

if ! command -v ros2 &> /dev/null; then
    echo "Error: ros2 CLI not found in PATH."
    echo "Please source your ROS 2 environment first, e.g.:"
    echo "  source /opt/ros/humble/setup.bash"
    exit 1
fi

if [ ! -f "$ROS2_DIR/install/setup.bash" ]; then
    echo "Workspace not built yet. Building now..."
    "$SCRIPT_DIR/build_ros2.sh"
fi

source "$ROS2_DIR/install/setup.bash"
echo "Launching ROS 2 simulation nodes..."
exec ros2 launch cdpr_bringup simulation.launch.py
