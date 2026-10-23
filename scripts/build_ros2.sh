#!/usr/bin/env bash
# Build ROS 2 CDPR Workspace on Ubuntu 24.04 (ROS 2 Jazzy) / Ubuntu 22.04 (ROS 2 Humble)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS2_DIR="$WORKSPACE_ROOT/ros2_ws"

echo "=== Building CDPR ROS 2 Workspace ==="

# Auto-source ROS 2 underlay if colcon/ros2 not already active in current shell
if ! command -v colcon &> /dev/null; then
    if [ -f /opt/ros/jazzy/setup.bash ]; then
        echo "Auto-sourcing ROS 2 Jazzy (/opt/ros/jazzy/setup.bash)..."
        source /opt/ros/jazzy/setup.bash
    elif [ -f /opt/ros/humble/setup.bash ]; then
        echo "Auto-sourcing ROS 2 Humble (/opt/ros/humble/setup.bash)..."
        source /opt/ros/humble/setup.bash
    else
        echo "Error: colcon not found and no ROS 2 installation detected in /opt/ros/{jazzy,humble}."
        echo "Please install ROS 2 Jazzy (Ubuntu 24.04) or source your environment:"
        echo "  source /opt/ros/jazzy/setup.bash"
        exit 1
    fi
fi

cd "$ROS2_DIR"

echo "Building packages with colcon in $ROS2_DIR..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo ""
echo "Build complete! To use the workspace, run:"
echo "  source $ROS2_DIR/install/setup.bash"
