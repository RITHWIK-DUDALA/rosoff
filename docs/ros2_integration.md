# ROS 2 Integration Guide

## 1. Overview & Distribution Compatibility

The CDPR project includes a full native ROS 2 workspace located under `ros2_ws/`. It coordinates kinematics, motion planning, state estimation, hardware communication abstraction, and visualization.

### 1.1 Supported Distributions
- **Primary Supported Target:** ROS 2 Humble Hawksbill (Ubuntu 22.04 LTS).
- **Secondary Supported Target:** ROS 2 Iron Irwini / Jazzy Jalisco (Ubuntu 24.04 LTS).
- **Host Operating System:** Ubuntu Linux (Native or WSL2).
  > **Note:** The core Python backend and Three.js digital twin run natively on Windows, macOS, or Linux in simulation mode without requiring ROS 2 to be installed. ROS 2 is required for physical distributed robotics coordination and micro-ROS agent bridging.

---

## 2. Package Architecture

The workspace `ros2_ws/src/` is structured into seven modular packages:

```text
ros2_ws/src/
├── cdpr_interfaces/        # Custom messages, services, and action definitions
├── cdpr_description/       # URDF/xacro model matching canonical 500x400x120 mm geometry
├── cdpr_kinematics/        # Analytical inverse kinematics, Jacobian, and target validation
├── cdpr_motion/            # Trapezoidal trajectory planner and motion coordinator
├── cdpr_state_estimator/   # Forward kinematics least-squares pose estimator & tracking error
├── cdpr_hardware/          # Simulator driver and hardware abstraction adapter
└── cdpr_bringup/           # System launch files and parameter configurations
```

### 2.1 `cdpr_interfaces`
Defines communication contracts:
- `msg/RobotState.msg`: Cartesian pose $(x, y)$, platform velocity $(\dot{x}, \dot{y})$, trajectory progress, and operational status.
- `msg/CableState.msg`: Geometric lengths $[l_1, l_2, l_3, l_4]$, commanded lengths, speeds, and tensions.
- `msg/MotorState.msg`: Actuator angular positions, speeds (RPM), torques, and drive fault codes.
- `msg/RobotDiagnostics.msg`: Latch faults, E-Stop state, boundary clearances, and provenance tags.
- `srv/ValidateTarget.srv`: Request Cartesian target $(x, y)$ validation; returns feasibility, lengths, speeds, and condition number.
- `srv/GetRobotConfiguration.srv`: Exposes canonical frame anchors, platform attachments, and safety boundaries.
- `srv/SetOperatingMode.srv`: Request switch between `SIMULATION`, `HARDWARE`, and `HARDWARE_DISABLED`.
- `action/MovePlatform.action`: Asynchronous Cartesian point-to-point trajectory execution with feedback.

### 2.2 `cdpr_description`
Contains the parametric URDF/Xacro representation:
- `urdf/cdpr.urdf.xacro`: Structural frame ($500 \times 400 \times 120\text{ mm}$), moving end-effector ($100 \times 80 \times 6\text{ mm}$), 4 spools, and 4 virtual prismatic joints representing cable line-of-action vectors.

### 2.3 `cdpr_kinematics`
- **Node:** `kinematics_node`
- Computes analytical cable lengths $l_i = \|\mathbf{p} + \mathbf{B}_i - \mathbf{A}_i\|$ and Jacobian matrix $\mathbf{J}_L \in \mathbb{R}^{4 \times 2}$.
- Provides the `/cdpr/kinematics/validate_target` service.

### 2.4 `cdpr_motion`
- **Node:** `motion_node`
- Executes deterministic trapezoidal velocity profile planning bounded by maximum platform velocity ($0.100\text{ m/s}$) and acceleration ($0.500\text{ m/s}^2$).
- Manages `/cdpr/command/target`, `/cdpr/command/jog`, and `/cdpr/command/stop`.

### 2.5 `cdpr_state_estimator`
- **Node:** `state_estimator_node`
- Consumes measured/simulated cable lengths, executes Levenberg-Marquardt least-squares forward kinematics, calculates tracking residuals $\|\mathbf{p}_{\text{target}} - \hat{\mathbf{p}}\|$, and detects stale feedback ($> 500\text{ ms}$).

### 2.6 `cdpr_hardware`
- **Node:** `simulator_node`: Physics simulation driver operating at 100 Hz.
- **Node:** `hardware_node`: Hardware adapter communicating with micro-ROS / ESP32. Blocks motion if unverified.

### 2.7 `cdpr_bringup`
- Consolidates system configuration (`config/ros2_params.yaml`) and launch scripts.

---

## 3. Interfaces: Topics, Services, and Actions

| Interface Name | Type | Direction / Role | QoS Policy |
|---|---|---|---|
| `/cdpr/state` | `cdpr_interfaces/msg/RobotState` | Pub (Coordinator) | Reliable, Volatile, Depth 10 |
| `/cdpr/cables/state` | `cdpr_interfaces/msg/CableState` | Pub (Hardware/Sim) | Reliable, Volatile, Depth 10 |
| `/cdpr/motors/state` | `cdpr_interfaces/msg/MotorState` | Pub (Hardware/Sim) | Reliable, Volatile, Depth 10 |
| `/cdpr/diagnostics` | `cdpr_interfaces/msg/RobotDiagnostics` | Pub (Diagnostics) | Reliable, Transient Local, Depth 1 |
| `/cdpr/command/target` | `geometry_msgs/msg/Point` | Sub (Motion) | Reliable, Volatile, Depth 10 |
| `/cdpr/command/stop` | `std_msgs/msg/Empty` | Sub (Emergency/Stop) | Reliable, Volatile, Depth 10 |
| `/cdpr/kinematics/validate_target` | `cdpr_interfaces/srv/ValidateTarget` | Service Server | Reliable |
| `/cdpr/config/get` | `cdpr_interfaces/srv/GetRobotConfiguration` | Service Server | Reliable |
| `/cdpr/mode/set` | `cdpr_interfaces/srv/SetOperatingMode` | Service Server | Reliable |
| `/cdpr/motion/move_platform` | `cdpr_interfaces/action/MovePlatform` | Action Server | Reliable |

---

## 4. Building the ROS 2 Workspace

### 4.1 Prerequisites
On Ubuntu 22.04 LTS:
```bash
sudo apt update && sudo apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-desktop
sudo rosdep init && rosdep update
```

### 4.2 Build Steps
From the repository root:
```bash
# Sourcing ROS 2 base environment
source /opt/ros/humble/setup.bash

# Navigate to workspace
cd ros2_ws

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y

# Build with colcon
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Source local workspace overlay
source install/setup.bash
```

---

## 5. Running Nodes and Launch Files

### 5.1 Simulation Mode (Default)
To launch the complete simulated digital twin in ROS 2:
```bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup simulation.launch.py
```
This starts:
- `kinematics_node`
- `motion_node`
- `simulator_node`
- `state_estimator_node`
- `robot_state_publisher` (URDF)

### 5.2 Micro-ROS Agent Bridge
To start the micro-ROS agent bridging the ESP32 microcontroller over USB serial:
```bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup micro_ros_agent.launch.py transport:=serial device:=/dev/ttyUSB0 baudrate:=115200
```
Or over UDP/Wi-Fi:
```bash
ros2 launch cdpr_bringup micro_ros_agent.launch.py transport:=udp port:=8888
```

### 5.3 Hardware Commissioning Mode (Guarded)
```bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup bringup.launch.py operating_mode:=HARDWARE
```
> **Safety Guard:** If hardware specifications or commissioning checks are unverified, `hardware_node` logs an error and refuses to arm physical drives.

---

## 6. Troubleshooting

1. **`colcon build` fails on interface generation:**
   Ensure `cdpr_interfaces` is built first:
   ```bash
   colcon build --packages-select cdpr_interfaces
   source install/setup.bash
   colcon build
   ```
2. **Missing Python dependencies in ROS 2 nodes:**
   Ensure NumPy and PyYAML are accessible to Python 3 in the ROS 2 environment:
   ```bash
   pip install numpy pyyaml scipy
   ```
3. **QoS Mismatch:**
   Ensure publishers and subscribers share matching durability and reliability settings. All motion commands and states use `Reliable` QoS to prevent silent packet loss.
