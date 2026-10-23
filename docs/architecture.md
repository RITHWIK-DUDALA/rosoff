# SYSTEM ARCHITECTURE: 2-DOF PLANAR CABLE-DRIVEN PARALLEL ROBOT (CDPR)
## Digital Twin, Python Backend, ROS 2, micro-ROS, ESP32, and Servo Drives

---

## 1. System Overview

The CDPR platform is an engineering-grade digital-twin and hardware-integration system designed for a two-degree-of-freedom planar cable-driven parallel robot. The architecture separates safe offline deterministic simulation from physical hardware commissioning through an explicit Hardware Abstraction Layer (HAL).

```
+-----------------------------------------------------------------------------------+
| OPERATOR BROWSER CLIENT (Three.js 3D Digital Twin + 2D Engineering View)          |
| - Target X/Y coordinate dispatch & bounded jogging                               |
| - Live 3D robot pose visualization & tension color indicators                     |
| - Provenance badges: Commanded, Simulated, Measured, Estimated                    |
| - Mode selector: Mode A (SIMULATION) vs Mode B (HARDWARE)                         |
| - WebSocket real-time telemetry streaming (30 Hz)                                 |
+-----------------------------------------------------------------------------------+
                                   | REST Commands (HTTP /api)
                                   | Telemetry Stream (WS /ws/telemetry)
                                   v
+-----------------------------------------------------------------------------------+
| PYTHON APPLICATION BACKEND (FastAPI + Asyncio)                                    |
|                                                                                   |
|   [REST API & WebSocket Handlers]                                                 |
|                 |                                                                 |
|   [Hardware Abstraction Layer (HAL)]                                              |
|                 +--------------------------------+                                |
|                 |                                |                                |
|                 v                                v                                |
|   [SimulatorDriver] (Active Mode A)    [HardwareDriver] (Active Mode B)           |
|   - Deterministic 100 Hz physics       - Communication with ROS 2 / micro-ROS     |
|   - Closed-form IK & Jacobian          - Strict unverified capability locks       |
|   - Tension allocation (lsq_linear)    - Safe Torque Off enforcement              |
|   - State estimation (FK solver)       - Homing state machine (UNREFERENCED guard)|
+-----------------------------------------------------------------------------------+
                                   |
                                   | ROS 2 Topics / Services / Actions
                                   v
+-----------------------------------------------------------------------------------+
| ROS 2 COORDINATION LAYER (ros2_ws)                                                |
| - cdpr_interfaces: Custom msg/srv/action (RobotState, CableState, MotorState)     |
| - cdpr_description: URDF/Xacro geometry (500x400 mm frame, 100x80 mm platform)   |
| - cdpr_kinematics: Analytical IK & Jacobian nodes                                 |
| - cdpr_motion: Trapezoidal velocity trajectory coordinator                        |
| - cdpr_state_estimator: Forward kinematics platform pose reconstruction           |
| - cdpr_hardware: Driver nodes (Simulator vs Hardware)                             |
| - cdpr_bringup: Launch files for simulation and hardware commissioning            |
+-----------------------------------------------------------------------------------+
                                   |
                                   | Serial UART (115200 baud) or Wi-Fi UDP
                                   v
+-----------------------------------------------------------------------------------+
| MICRO-ROS AGENT (Host Computer daemon)                                            |
+-----------------------------------------------------------------------------------+
                                   | XRCE-DDS Transport
                                   v
+-----------------------------------------------------------------------------------+
| ESP32 MICROCONTROLLER CLIENT (FreeRTOS Firmware)                                  |
| - Finite State Machine: BOOT -> INITIALIZING -> WAITING_FOR_AGENT -> CONNECTED    |
|   -> DRIVE_STATUS_CHECK -> READY -> MOTION_ENABLED -> SAFE_STOP / FAULT           |
| - 250 ms communication timeout watchdog                                           |
| - Anti-auto-arm protection on reconnection                                        |
+-----------------------------------------------------------------------------------+
                                   | Protocol-Agnostic Interface (CAN-FD / RS-485)
                                   v
+-----------------------------------------------------------------------------------+
| 4x SERVO DRIVES, MOTORS, AND SPOOL DRUMS (r = 10 mm)                              |
+-----------------------------------------------------------------------------------+
                                   | Measured Encoders / Drive Feedback
                                   +-------- Feedback Path (Closed-Loop) ----------->
```

---

## 2. Operating Modes (Section 3)

The architecture supports two mutually exclusive, explicitly selected operating modes:

### Mode A: SIMULATION (Default)
- **Active Driver:** `SimulatorDriver`
- **Hardware Requirement:** None. Operates completely offline without ESP32, servo drives, micro-ROS agent, or ROS 2.
- **Physical Safety:** Physical motor outputs are never energized.
- **Data Provenance:** All position, velocity, and cable length states are explicitly labeled with `provenance: "simulated"`.
- **Intended Use:** Trajectory planning, algorithm verification, control law tuning, UI operator training.

### Mode B: HARDWARE (Commissioning)
- **Active Driver:** `HardwareDriver`
- **Prerequisites:**
  1. Complete hardware capability profile verified (`hardware_profile.yaml`).
  2. Verified communication connection to micro-ROS client.
  3. Independent physical emergency stop verified.
  4. Platform referenced via verified physical homing sequence (`homing_state: "HOMED"`).
  5. Zero unacknowledged drive faults.
- **Enforcement:** If any hardware capability remains `unknown` or `unverified`, the backend automatically transitions to `HARDWARE_DISABLED` and strictly refuses coordinate motion commands.
- **Data Provenance:** Position is reconstructed from measured drive encoder feedback via Forward Kinematics and tagged `provenance: "estimated"` or `"measured"`.

---

## 3. Communication and Data Flow

### 3.1 Motion Command Pipeline
1. **Operator Input:** Operator submits target coordinates $(x, y)$ in mm via REST (`POST /api/command/move`) or Web UI.
2. **Boundary Validation:** The HAL checks coordinates against canonical workspace limits ($[-180, +180]\text{ mm}$, $[-140, +140]\text{ mm}$).
3. **Kinematics Calculation:** Analytical inverse kinematics computes the 4 required cable lengths:
   $$L_i = \|A_i - (q + B_i)\|$$
4. **Trajectory Generation:** Trapezoidal velocity profiling generates interpolated waypoints honoring maximum speed ($100\text{ mm/s}$) and acceleration ($500\text{ mm/s}^2$).
5. **Feasibility Verification:** Multi-point path validation confirms that cable speeds do not exceed $300\text{ RPM}$ and unilateral cable tensions satisfy $2\text{ N} \le T_i \le 300\text{ N}$.
6. **Execution Dispatch:**
   - In **Mode A**, the deterministic physics engine advances platform state at 100 Hz.
   - In **Mode B**, commands are transmitted via micro-ROS to the ESP32.

### 3.2 Feedback and State Estimation Pipeline
1. Actuators report cable lengths $L_{meas}$ (either simulated or measured from physical drive encoders).
2. The `StateEstimator` executes a damped Gauss-Newton / Levenberg-Marquardt solver to reconstruct platform coordinates $\hat{q} = [\hat{x}, \hat{y}]$.
3. Residual norms $\|L(\hat{q}) - L_{meas}\|$ and Jacobian condition numbers $\kappa(J_L)$ are computed.
4. If residual error $< 20\text{ mm}$ and estimate is fresh ($< 500\text{ ms}$), tracking error is calculated:
   $$\text{error} = \|q_{target} - \hat{q}\|$$
5. Telemetry packets are broadcast over WebSocket (`/ws/telemetry`) at 30 Hz.
6. The Three.js digital twin updates the 3D model and diagnostic plots.

---

## 4. Hardware Abstraction Layer (HAL) Contract

All drivers implement the abstract `RobotDriver` interface:

| Method | SimulatorDriver Behavior | HardwareDriver Behavior |
|---|---|---|
| `connect()` | Returns immediate success. | Verifies hardware readiness; fails if profile unverified. |
| `disconnect()` | Sets connected flag to false. | Asserts Safe Torque Off on all drives. |
| `get_status()` | Returns simulation state. | Returns hardware profile, verification checklist, missing items. |
| `read_state()` | Returns simulated telemetry. | Returns encoder measurements or `UNAVAILABLE` if disabled. |
| `validate_command()` | Checks workspace & trajectory. | Checks workspace, homing status, and physical readiness. |
| `request_move()` | Queues motion in simulation. | Refuses motion if hardware unverified or unhomed. |
| `request_stop()` | Smoothly stops active trajectory. | Clamps drive velocity demands to zero immediately. |
| `request_estop()` | Latches software E-stop. | Engages STO; requires physical inspection before reset. |
| `reset_recoverable_fault()` | Resets simulation to origin. | Refuses to clear physical hardware faults via software. |

---

## 5. Rate Decoupling and Timing

To guarantee system stability, the architecture intentionally decouples execution frequencies:

| Loop | Nominal Rate | Implementation | Purpose |
|---|---|---|---|
| Browser Render Loop | 60 Hz | Three.js `requestAnimationFrame` | Visual smoothness |
| Telemetry Broadcast | 30 Hz | FastAPI WebSocket loop | Network bandwidth conservation |
| Simulation Physics Loop | 100 Hz ($dt=10\text{ ms}$) | Python asyncio background task | Deterministic dynamic integration |
| Trajectory Interpolation | 50 Hz | ROS 2 / Python planner | Kinematic setpoint dispatch |
| ESP32 Watchdog / FSM | 50 Hz | FreeRTOS periodic task | Comm-loss monitoring and drive servicing |
| Servo Drive Internal Loop | 1 kHz - 20 kHz | Onboard servo drive DSP / FOC | Current, velocity, and position control |
