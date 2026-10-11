# ROS 2 INTEGRATION INTERFACE (OPTIONAL)

## 1. Overview
The CDPR simulator can operate completely independently without ROS installed (via its native FastAPI REST and WebSocket interfaces).

For robotics workflows integrating with ROS 2 (e.g. Humble, Iron, or Rolling), this directory provides an optional ROS 2 bridge node (`cdpr_ros2_bridge.py`).

## 2. Topic Interface
- **Subscriptions**:
  - `/cdpr/command/move` (`geometry_msgs/msg/PointStamped` or `std_msgs/msg/String` JSON): Dispatches target coordinates $[x, y]$ to the simulator.
  - `/cdpr/command/estop` (`std_msgs/msg/Empty`): Triggers immediate simulated emergency stop.
- **Publications**:
  - `/cdpr/robot_state` (`sensor_msgs/msg/JointState`): Publishes cable lengths as position, cable rates as velocity, and cable tensions as effort for cables `cable_1` to `cable_4`.
  - `/cdpr/pose` (`geometry_msgs/msg/PoseStamped`): Publishes current simulated platform pose.
  - `/diagnostics` (`diagnostic_msgs/msg/DiagnosticArray`): Publishes condition number, tracking error, tension feasibility, and fault flags.

## 3. Running the ROS 2 Bridge
Prerequisites: A standard ROS 2 installation (Humble/Iron) and Python `rclpy`.

```bash
# 1. Start the CDPR simulation backend:
python -m backend.main

# 2. In your ROS 2 environment:
source /opt/ros/humble/setup.bash
python ros2/cdpr_ros2_bridge.py
```

*Note*: This interface operates as a network bridge over REST/WebSocket and does not require building custom C++ packages.
