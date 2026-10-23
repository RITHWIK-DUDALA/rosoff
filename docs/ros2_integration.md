# ROS 2 Integration Guide: Ubuntu 24.04 LTS (Jazzy) & Ubuntu 22.04 LTS (Humble)

## 1. Overview & Distribution Compatibility

The CDPR project includes a full native ROS 2 workspace located under `ros2_ws/`. It coordinates kinematics, motion planning, state estimation, hardware communication abstraction, and visualization.

### 1.1 Supported Distributions
- **Primary Supported Target:** **ROS 2 Jazzy Jalisco (Ubuntu 24.04 LTS Noble Numbat, Python 3.12)**.
- **Backwards-Compatible Target:** **ROS 2 Humble Hawksbill (Ubuntu 22.04 LTS Jammy Jellyfish, Python 3.10)**.
- **Host Operating System:** Ubuntu Linux (Native or WSL2).
  > **Note:** The core Python backend and Three.js digital twin run natively on Windows, macOS, or Linux in simulation mode without requiring ROS 2 to be installed. ROS 2 is required for physical distributed robotics coordination and micro-ROS agent bridging.

### 1.2 Key Differences & Jazzy (Ubuntu 24.04) Considerations
1. **Python 3.12 & PEP 668:** Ubuntu 24.04 enforces externally-managed Python environments. When installing Python dependencies, use system packages (`python3-numpy`, `python3-scipy`) or a virtual environment created with `--system-site-packages` so `/opt/ros/jazzy/lib/python3.12/site-packages` remains visible to `rclpy`.
2. **Setup Configurations (`setup.cfg`):** Every `ament_python` package in `ros2_ws/src/` specifies `[install] install_scripts=$base/lib/<package_name>` to ensure colcon places node binaries into the correct ROS 2 execution path.
3. **Rosdep Keys:** Added `<depend>python3-numpy</depend>` across packages so `rosdep install` automatically resolves and installs NumPy.

---

## 2. Package Architecture

The workspace `ros2_ws/src/` is structured into seven modular packages:

```text
ros2_ws/src/
├── cdpr_interfaces/        # Custom messages, services, and action definitions (ament_cmake)
├── cdpr_description/       # URDF/xacro model matching canonical 500x400x120 mm geometry (ament_cmake)
├── cdpr_kinematics/        # Analytical inverse kinematics, Jacobian, and target validation (ament_python)
├── cdpr_motion/            # Trapezoidal trajectory planner and motion coordinator (ament_python)
├── cdpr_state_estimator/   # Forward kinematics least-squares pose estimator & tracking error (ament_python)
├── cdpr_hardware/          # Simulator driver and hardware abstraction adapter (ament_python)
└── cdpr_bringup/           # System launch files and parameter configurations (ament_python)
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
- Subscribes to `/cdpr/command/target` and `/cdpr/motion/setpoint`.
- Publishes to `/cdpr/cables/command`.
- Provides the `/cdpr/validate_target` service.

### 2.4 `cdpr_motion`
- **Node:** `motion_node`
- Executes deterministic trapezoidal velocity profile planning bounded by maximum platform velocity ($0.100\text{ m/s}$) and acceleration ($0.500\text{ m/s}^2$).
- Publishes continuous trajectory setpoints at 50 Hz on `/cdpr/motion/setpoint`.
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
| `/cdpr/cables/command` | `sensor_msgs/msg/JointState` | Pub (Kinematics) | Reliable, Volatile, Depth 10 |
| `/cdpr/cables/feedback` | `sensor_msgs/msg/JointState` | Pub (Hardware/Sim) | Reliable, Volatile, Depth 10 |
| `/cdpr/motors/state` | `cdpr_interfaces/msg/MotorState` | Pub (Hardware/Sim) | Reliable, Volatile, Depth 10 |
| `/cdpr/diagnostics` | `cdpr_interfaces/msg/RobotDiagnostics` | Pub (Diagnostics) | Reliable, Transient Local, Depth 1 |
| `/cdpr/command/target` | `geometry_msgs/msg/Point` | Sub (Motion) | Reliable, Volatile, Depth 10 |
| `/cdpr/motion/setpoint` | `geometry_msgs/msg/Point` | Pub (Motion) / Sub (Kinematics) | Reliable, Volatile, Depth 10 |
| `/cdpr/command/stop` | `std_msgs/msg/Bool` | Sub (Emergency/Stop) | Reliable, Volatile, Depth 10 |
| `/cdpr/validate_target` | `cdpr_interfaces/srv/ValidateTarget` | Service Server | Reliable |
| `/cdpr/config/get` | `cdpr_interfaces/srv/GetRobotConfiguration` | Service Server | Reliable |
| `/cdpr/mode/set` | `cdpr_interfaces/srv/SetOperatingMode` | Service Server | Reliable |
| `/cdpr/motion/move_platform` | `cdpr_interfaces/action/MovePlatform` | Action Server | Reliable |

---

## 4. Building the ROS 2 Workspace

### 4.1 Prerequisites on Ubuntu 24.04 LTS (Jazzy)
```bash
sudo apt update && sudo apt install -y \
    curl \
    gnupg \
    lsb-release \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip \
    python3-numpy \
    ros-jazzy-desktop
sudo rosdep init 2>/dev/null || true
rosdep update
```

*(Note for Ubuntu 22.04: replace `ros-jazzy-desktop` with `ros-humble-desktop`)*

### 4.2 Build Steps
From the repository root:
```bash
# Option A: Automated Build Script (handles auto-sourcing)
./scripts/build_ros2.sh

# Option B: Manual colcon build
source /opt/ros/jazzy/setup.bash
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

---

## 5. Running Nodes and Launch Files

### 5.1 Simulation Mode (Default)
To launch the complete simulated digital twin in ROS 2:
```bash
# Automated launch
./scripts/run_ros2_simulation.sh

# Or manually:
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup simulation.launch.py
```
This starts:
1. `robot_state_publisher` (URDF model with analytical geometry)
2. `cdpr_kinematics_node` (Analytical IK and Jacobian matrix $\mathbf{J}_L$)
3. `cdpr_motion_node` (Trapezoidal 50 Hz trajectory generator)
4. `cdpr_simulator_node` (Deterministic cable actuator physics)
5. `cdpr_state_estimator_node` (Levenberg-Marquardt FK pose reconstruction)

### 5.2 Micro-ROS Agent Bridge
To start the micro-ROS agent bridging the ESP32 microcontroller over USB serial on Jazzy:
```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup micro_ros_agent.launch.py transport:=serial device:=/dev/ttyUSB0 baudrate:=115200
```
Or via Docker on Ubuntu 24.04:
```bash
docker run -it --rm --net=host --privileged -v /dev:/dev \
    microros/micro-ros-agent:jazzy \
    serial --dev /dev/ttyUSB0 -b 115200
```

### 5.3 Hardware Commissioning Mode (Guarded)
```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch cdpr_bringup bringup.launch.py
```
> **Safety Guard:** If hardware specifications or commissioning checks are unverified, `cdpr_hardware_node` logs an error and refuses to arm physical drives.

---

## 6. Verification and Inspection Commands

Once running, verify system operation in separate terminals:
```bash
# Check running nodes
ros2 node list

# Check active topics
ros2 topic list

# Echo platform estimated state
ros2 topic echo /cdpr/state

# Send test target move command (X = 50 mm, Y = 40 mm)
ros2 topic pub --once /cdpr/command/target geometry_msgs/msg/Point "{x: 0.050, y: 0.040, z: 0.0}"

# Send controlled stop
ros2 topic pub --once /cdpr/command/stop std_msgs/msg/Bool "{data: true}"
```

---

## 7. Troubleshooting

1. **`colcon build` fails on interface generation:**
   Ensure `cdpr_interfaces` is built first:
   ```bash
   colcon build --packages-select cdpr_interfaces
   source install/setup.bash
   colcon build
   ```
2. **Missing Python dependencies in ROS 2 nodes:**
   On Ubuntu 24.04, install system packages to respect PEP 668:
   ```bash
   sudo apt install -y python3-numpy python3-scipy python3-yaml
   ```
3. **Node executable not found (`Package 'cdpr_kinematics' not found`):**
   Ensure `setup.cfg` exists in the package root and re-run `colcon build --symlink-install`.
4. **QoS Mismatch:**
   Ensure publishers and subscribers share matching durability and reliability settings. All motion commands and states use `Reliable` QoS to prevent silent packet loss.
