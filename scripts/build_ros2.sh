#!/usr/bin/env bash
# Build ROS 2 CDPR Workspace on Ubuntu Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS2_DIR="$WORKSPACE_ROOT/ros2_ws"

echo "=== Building CDPR ROS 2 Workspace ==="

if ! command -v colcon &> /dev/null; then
    echo "Error: colcon not found in PATH."
    echo "Please source your ROS 2 environment first, e.g.:"
    echo "  source /opt/ros/humble/setup.bash"
    exit 1
fi

cd "$ROS2_DIR"

echo "Building packages with colcon in $ROS2_DIR..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo ""
echo "Build complete! To use the workspace, run:"
echo "  source $ROS2_DIR/install/setup.bash"
