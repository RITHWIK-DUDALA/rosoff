#!/usr/bin/env bash
# Build ESP32 micro-ROS Firmware on Ubuntu Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FW_DIR="$WORKSPACE_ROOT/firmware/esp32_micro_ros"

echo "=== Building ESP32 micro-ROS Firmware ==="

if ! command -v idf.py &> /dev/null; then
    echo "Error: idf.py not found in PATH."
    echo "Please source your ESP-IDF environment first, e.g.:"
    echo "  source ~/esp/esp-idf/export.sh"
    echo "See docs/micro_ros_setup.md for full toolchain setup."
    exit 1
fi

cd "$FW_DIR"

echo "Setting target to esp32..."
idf.py set-target esp32

echo "Building firmware..."
idf.py build

echo ""
echo "Build complete! To flash connected ESP32, run:"
echo "  idf.py -p /dev/ttyUSB0 flash monitor"
