# Planar Cable-Driven Parallel Robot (CDPR) Simulator

Engineering-grade 2-DOF planar Cable-Driven Parallel Robot simulator featuring real analytical kinematics, forward position reconstruction, quadratic static tension allocation, actuator saturation constraints, fixed-timestep physics loop, live Three.js 3D viewport, 2D dimensioned orthographic projection, and real-time telemetry streaming.

---

## 1. Specifications Overview

| Parameter | Value |
|---|---|
| **Robot Type** | 2-DOF Planar Cable-Driven Parallel Robot |
| **Motion Plane** | Horizontal XY Plane (Gravity along -Z supported by bed & guide rods) |
| **Frame Geometry** | $500 \times 400 \times 120\text{ mm}$ inner bounding envelope |
| **Platform Footprint** | $100 \times 80 \times 6\text{ mm}$, Mass: $0.5\text{ kg}$ |
| **Safe Workspace** | $X \in [-180, +180]\text{ mm}$, $Y \in [-140, +140]\text{ mm}$ (with 20 mm boundary clearance) |
| **Actuation** | 4 spools, drum radius $r = 10\text{ mm}$ |
| **Actuator Limits** | Speed $\le 300\text{ RPM}$, Torque $\le 0.40\text{ Nm}$ (provisional bounds) |
| **Nominal Speed** | $100\text{ mm/s}$ maximum platform translational speed |
| **Simulation Timestep** | Fixed $\Delta t = 10\text{ ms}$ (100 Hz deterministic physics engine) |
| **Telemetry Rate** | 30 Hz WebSocket broadcast to browser clients |

---

## 2. Directory Structure

```text
rosoff/
├── robot_config.yaml         # Single source of truth configuration
├── pytest.ini                # Pytest configuration
├── backend/
│   ├── main.py               # FastAPI server and background simulation loop
│   ├── requirements.txt      # Python dependencies
│   ├── api/
│   │   ├── routes.py         # REST endpoints (/health, /command/*, /workspace, etc.)
│   │   └── websocket.py      # /ws/telemetry live WebSocket streamer
│   └── cdpr/
│       ├── config.py         # Strict YAML validator and SI conversion
│       ├── geometry.py       # Anchor and platform attachment vector mathematics
│       ├── kinematics.py     # Inverse kinematics, Jacobian J_L, and Levenberg-Marquardt FK
│       ├── tension_solver.py # Bounded quadratic programming static tension allocation
│       ├── actuator.py       # Drum spooling, RPM, and torque saturation models
│       ├── dynamics.py       # Reduced-coordinate planar platform dynamic simulation
│       ├── collision.py      # Footprint, frame clearance, and cable bounds checking
│       ├── trajectory.py     # Trapezoidal point-to-point, circle, rectangle, waypoints
│       ├── controller.py     # Motion supervisor state machine and jogging
│       ├── simulation.py     # Fixed-timestep physics simulation engine
│       └── state.py          # Telemetry and state data structures
├── frontend/
│   ├── index.html            # Dual-viewport engineering interface
│   ├── style.css             # Dark high-contrast engineering stylesheet
│   ├── app.js                # Frontend bootstrap and state synchronization
│   └── modules/
│       ├── scene.js          # Three.js 3D scene, lighting, and camera management
│       ├── robot_view.js     # 3D frame, winches, cables, platform, guide rods
│       ├── engineering_view.js # 2D dimensioned millimeter orthographic projection
│       ├── telemetry.js      # WebSocket client with auto-reconnect
│       ├── controls.js       # Move, jog, preset, pause, stop, e-stop handlers
│       └── plots.js          # Real-time diagnostic chart renderers
├── tests/
│   ├── test_geometry.py      # Geometry and coordinate symmetry tests
│   ├── test_kinematics.py    # Analytical vs finite-difference Jacobian, IK, and FK recovery
│   ├── test_tension.py       # Equilibrium residuals, non-negativity, and extreme force rejection
│   ├── test_actuator.py      # Drum spooling, RPM calculations, and saturation flags
│   ├── test_trajectory.py    # Path feasibility, speed limits, and boundary violation rejection
│   ├── test_simulation.py    # Deterministic simulation stepping and E-stop integration
│   └── test_api.py           # REST endpoints and validation responses
├── scripts/
│   └── generate_plots.py     # Offline verification plot generation using solver outputs
├── docs/
│   ├── MODEL.md              # Physical model, equations, and sign conventions
│   ├── ASSUMPTIONS.md        # Provisional parameters and unverified hardware assumptions
│   ├── VALIDATION.md         # Numerical validation test log and verification results
│   ├── HARDWARE.md           # Component selection guidelines for physical testbed
│   ├── workspace_feasibility.png
│   ├── cable_lengths_vs_position.png
│   ├── motor_rpm_trajectory.png
│   ├── cable_tensions_time.png
│   └── tracking_error_trajectory.png
└── ros2/
    ├── README.md             # ROS 2 integration guide
    └── cdpr_ros2_bridge.py   # Optional ROS 2 node bridging JointState and Pose topics
```

---

## 3. Installation and Quickstart

### 3.1 Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3.2 Run Automated Tests
```bash
pytest tests/ -v
```
All 25 unit and integration tests run in under 5 seconds.

### 3.3 Launch Application
```bash
python -m backend.main
```
Open your browser to:
[http://localhost:8000](http://localhost:8000)

The web client connects automatically to the backend over WebSocket and streams real-time telemetry.

### 3.4 Generate Offline Engineering Plots
```bash
python -m scripts.generate_plots
```
Saves high-resolution verification charts directly into the `docs/` folder.
