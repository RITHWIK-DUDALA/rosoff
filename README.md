# Planar Cable-Driven Parallel Robot (CDPR) Platform
### 2-DOF, Four-Cable Digital Twin + Python Backend + ROS 2 + micro-ROS + ESP32 + Servo Drives

Engineering-grade, mathematically verified digital twin and hardware integration platform for a two-degree-of-freedom planar Cable-Driven Parallel Robot (CDPR). Features real analytical kinematics, Levenberg-Marquardt forward kinematics pose estimation, quadratic static tension allocation, actuator saturation constraints, strict hardware safety interlocks, interactive Three.js 3D viewport, 2D dimensioned engineering projection, modular ROS 2 workspace, and an ESP32 micro-ROS embedded firmware client.

---

## 1. System Architecture

The platform bridges operator commands in the browser down to micro-ROS embedded firmware and servo drives:

```text
+-------------------------------------------------------------+
| Browser Engineering Interface (Three.js + Orthographic 2D) |
| - Interactive 3D Digital Twin & Dimensioned 2D Projection    |
| - Target X/Y, Jogging, Controlled Stop, Mode Selection       |
+-------------------------------------------------------------+
                              |
                     WebSocket / REST API
                              v
+-------------------------------------------------------------+
| Python Application Backend (FastAPI + SciPy + NumPy)       |
| - Canonical Configuration & JSON Schema Validation          |
| - Analytical IK & Jacobian (J_L)                           |
| - Levenberg-Marquardt Forward Kinematics State Estimator    |
| - Bounded Quadratic Programming Tension Solver (lsq_linear) |
| - Deterministic 100 Hz Physics Loop & Provenance Tagging    |
| - Hardware Abstraction Layer (HAL) & Safety Interlocks      |
+-------------------------------------------------------------+
                              |
                       ROS 2 Humble DDS
                              v
+-------------------------------------------------------------+
| ROS 2 Workspace (ros2_ws/)                                  |
| - cdpr_interfaces (Messages, Services, Actions)             |
| - cdpr_description (Parametric URDF/Xacro)                 |
| - cdpr_kinematics, cdpr_motion, cdpr_state_estimator        |
| - cdpr_hardware (Simulation Driver + Hardware Driver)       |
+-------------------------------------------------------------+
                              |
                    micro-ROS Agent (Serial/UDP)
                              v
+-------------------------------------------------------------+
| Embedded Microcontroller (firmware/esp32_micro_ros/)       |
| - ESP32 SoC running FreeRTOS & micro-ROS Client             |
| - Strict Finite State Machine & 250 ms Hardware Watchdog    |
| - Isolated Servo Driver Interface Layer                     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Actuation & Mechanics                                       |
| - 4x Spool Winches (r = 10 mm drum radius)                  |
| - 4x Servo Motors & Drives with Safe Torque Off (STO)       |
| - Moving Platform (100x80x6 mm, mass = 0.5 kg)              |
+-------------------------------------------------------------+
```

---

## 2. Supported Operating Modes

1. **`SIMULATION` (Default):**
   - Pure offline mathematical simulation.
   - Requires zero external hardware and zero ROS 2 dependencies.
   - All generated telemetry is explicitly tagged with `provenance: "simulated"`.
   - Guaranteed safe for development, algorithm verification, and operator training.

2. **`HARDWARE_DISABLED`:**
   - Connects to hardware or ROS 2 interfaces for diagnostics and sensor monitoring only.
   - Actuator torque commands are disabled in software.
   - Allows safe inspection of encoder registers and drive health.

3. **`HARDWARE` (Guarded):**
   - Active physical robot control mode.
   - **Strict Safety Gate:** Refuses activation if any hardware parameters remain `unverified`, if homing is unreferenced, or if safety interlocks are tripped.
   - Motors are NEVER energized automatically upon connection or application boot.

---

## 3. Canonical Robot Geometry & Specifications

All geometry is defined in a single source of truth (`config/robot_config.yaml`):

| Parameter | Value | Notes |
|---|---|---|
| **Controlled DOF** | 2 Translational ($X, Y$) | Anti-rotation guide rods constrain $\theta_z$ |
| **Number of Cables** | 4 | Antagonistic planar configuration |
| **Frame Dimensions** | $500 \times 400 \times 120\text{ mm}$ | Outer aluminum extrusion boundary |
| **Platform Dimensions** | $100 \times 80 \times 6\text{ mm}$ | Aluminum end-effector plate |
| **Platform Mass** | $0.50\text{ kg}$ | Provisional design value |
| **Safe Workspace** | $X \in [-180, +180]\text{ mm}$, $Y \in [-140, +140]\text{ mm}$ | 20 mm clearance from frame edges |
| **Spool Drum Radius** | $r = 10.0\text{ mm}$ ($0.010\text{ m}$) | Nominal spool cylinder radius |
| **Nominal Speed** | $100\text{ mm/s}$ ($0.100\text{ m/s}$) | Maximum platform translational speed |
| **Actuator Limits** | $\le 300\text{ RPM}$, $\le 0.40\text{ Nm}$ | Provisional drive boundaries |
| **Frame Anchors** | $A_1: (-250, +200)$, $A_2: (+250, +200)$, $A_3: (+250, -200)$, $A_4: (-250, -200)\text{ mm}$ | Frame corner pulleys |
| **Platform Attachments** | $B_1: (-50, +40)$, $B_2: (+50, +40)$, $B_3: (+50, -40)$, $B_4: (-50, -40)\text{ mm}$ | Local platform anchor points |

---

## 4. Repository Layout

```text
rosoff/
├── config/
│   ├── robot_config.yaml         # Single source of truth configuration
│   ├── configuration.schema.json # JSON Schema for strict validation
│   └── hardware_profile.example.yaml # Capability verification template
├── backend/
│   ├── main.py                   # FastAPI application entry point
│   ├── requirements.txt          # Python dependencies
│   ├── api/                      # REST endpoints & WebSocket streamer
│   └── cdpr/                     # Core robotics mathematics, HAL, and simulation
├── frontend/
│   ├── index.html                # Dual-viewport engineering interface
│   ├── style.css                 # Industrial high-contrast stylesheet
│   ├── app.js                    # Bootstrap & state coordinator
│   └── modules/                  # Three.js 3D viewport, 2D projection, telemetry
├── ros2_ws/
│   └── src/
│       ├── cdpr_interfaces/      # Custom ROS 2 msgs, srvs, actions
│       ├── cdpr_description/     # Parametric URDF/Xacro representation
│       ├── cdpr_kinematics/      # Kinematics and target validation node
│       ├── cdpr_motion/          # Trapezoidal motion planning node
│       ├── cdpr_state_estimator/ # Forward kinematics state estimation node
│       ├── cdpr_hardware/        # Simulation and hardware driver nodes
│       └── cdpr_bringup/         # System launch files and parameter files
├── firmware/
│   └── esp32_micro_ros/          # ESP32 FreeRTOS micro-ROS client project
│       ├── CMakeLists.txt
│       ├── sdkconfig.defaults
│       └── main/                 # FSM, servo driver interface, watchdog
├── scripts/
│   ├── setup_dev.sh / .ps1       # Environment setup script
│   ├── run_simulation.sh / .ps1  # Launch backend and simulation
│   ├── run_tests.sh / .ps1       # Run full automated test suite
│   ├── start_ros2.sh / .ps1      # Build and launch ROS 2 workspace
│   ├── diagnostics.sh / .ps1     # System health and configuration check
│   └── benchmark_performance.py  # Algorithmic execution time profiler
└── docs/
    ├── architecture.md           # Detailed system architecture
    ├── robot_geometry.md         # Coordinate frames and anchor vectors
    ├── kinematics.md             # Equations for IK, Jacobian, FK, and tension
    ├── ros2_integration.md       # ROS 2 build, launch, and QoS guide
    ├── micro_ros_setup.md        # ESP32 firmware build, flash, and agent guide
    ├── hardware_setup.md         # Hardware capability audit and wiring rules
    ├── commissioning.md          # 7-stage physical commissioning workflow
    ├── safety.md                 # Safety architecture and risk mitigations
    ├── troubleshooting.md        # Comprehensive diagnostic checklist
    └── validation_report.md      # Test logs, timing benchmarks, blocked items
```

---

## 5. Quickstart & Execution Commands

### 5.1 System Diagnostics & Health Check
Verify your environment and configuration:
```powershell
.\scripts\diagnostics.ps1
# Or on Linux: ./scripts/diagnostics.sh
```

### 5.2 Run Automated Tests
Execute the comprehensive 37-test suite:
```powershell
.\scripts\run_tests.ps1
# Or directly: python -m pytest tests/ -v
```

### 5.3 Launch Browser Digital Twin & Simulation Backend
```powershell
.\scripts\run_simulation.ps1
# Or directly: python -m backend.main
```
Open your browser to:
**[http://localhost:8000](http://localhost:8000)**

### 5.4 Benchmark Mathematical Performance
```bash
python scripts/benchmark_performance.py
```

### 5.5 ROS 2 Workspace (Ubuntu 22.04 LTS / WSL2)
```bash
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch cdpr_bringup simulation.launch.py
```

### 5.6 ESP32 micro-ROS Firmware Build
```bash
cd firmware/esp32_micro_ros
idf.py set-target esp32
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

---

## 6. Algorithmic Performance Benchmarks

Measured on the development host (5,000 iterations):

| Component | Mean Execution Time | Frequency Capability | Requirement |
|---|---|---|---|
| **Inverse Kinematics + Jacobian** | $66.79\ \mu\text{s}$ | $14,972\text{ Hz}$ | $100\text{ Hz}$ ($150\times$ margin) |
| **Forward Kinematics (Levenberg-Marquardt)** | $427.36\ \mu\text{s}$ | $2,340\text{ Hz}$ | $100\text{ Hz}$ ($23\times$ margin) |
| **Static Tension Allocation (`lsq_linear`)** | $206.01\ \mu\text{s}$ | $4,854\text{ Hz}$ | $100\text{ Hz}$ ($48\times$ margin) |
| **Full Physics Simulation Step** | $641.91\ \mu\text{s}$ | $1,558\text{ Hz}$ | $100\text{ Hz}$ ($15.5\times$ margin) |

---

## 7. Current Limitations & Hardware Readiness

In strict adherence to Rules 0.2 and 0.3:
- **Provisional Hardware:** Exact motor models, drive communication protocols (CANopen vs Step/Dir vs Modbus), and encoder resolutions are not yet physically confirmed.
- **Safety Interlock:** Physical motor arming is intentionally locked in software until the physical commissioning checklist (`docs/commissioning.md`) is completed.
- **Offline First:** The digital twin is fully self-contained and operates without physical hardware or ROS 2 installed.
