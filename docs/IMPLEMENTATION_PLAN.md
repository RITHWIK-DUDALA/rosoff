# IMPLEMENTATION PLAN — ENGINEERING-GRADE PLANAR CABLE ROBOT SIMULATOR

## 1. Baseline Audit & Workspace State
- Workspace `rosoff` was initialized clean (empty directory).
- Python 3.11.9 available with core scientific libraries: `numpy`, `scipy`, `matplotlib`, `pytest`, `fastapi`, `uvicorn`, `pyyaml`, `websockets`.

## 2. Architecture & Modular Breakdown

### Directory Layout
- `robot_config.yaml`: Single source of truth for all mechanical, kinematic, actuator, limits, control, and visual specs.
- `backend/`
  - `cdpr/`
    - `config.py`: Strictly validates YAML schema, dimensional units, physical bounds.
    - `geometry.py`: Frame, platform attachments, anchor points in SI (meters), coordinate conventions (origin at center).
    - `kinematics.py`: Analytical inverse kinematics, Jacobian $J_L$, forward kinematics solver via Levenberg-Marquardt / damped Gauss-Newton with redundancy handling.
    - `tension_solver.py`: Bounded quadratic programming / active-set static force allocation solver with nonnegativity $T_i \ge T_{min}$, equilibrium residual checks, and infeasibility reporting.
    - `actuator.py`: Drum radius, spooling mechanics, motor RPM and torque calculations, speed & torque saturation, inertia and efficiency.
    - `dynamics.py`: Reduced-coordinate planar platform translational dynamics $M \ddot{q} = -J_L^T T + F_{ext}$, holonomic cable constraint residual evaluation.
    - `collision.py`: Footprint bounding boxes, frame boundary clearance, guide clearance, cable-frame interference.
    - `trajectory.py`: Point-to-point, straight-line, circular, rectangular, waypoint trajectories with trapezoidal/S-curve velocity profiles, comprehensive path feasibility checker (sampled intermediate points).
    - `controller.py`: Motion supervisor, command queue, jogging, pause/resume/stop/reset, emergency stop states.
    - `simulation.py`: Fixed-timestep deterministic simulation loop engine ($dt = 0.01$ s or configured), telemetry publisher.
    - `state.py`: Telemetry data classes and serialization schemas.
  - `api/`
    - `routes.py`: REST endpoints (`/health`, `/config`, `/state`, `/command/*`, `/workspace`, `/diagnostics`).
    - `websocket.py`: `/ws/telemetry` live high-rate streaming.
  - `main.py`: FastAPI server setup, static mount for frontend, lifecycle management.
- `frontend/`
  - `index.html`: Responsive engineering UI with dual-viewport (3D Three.js + 2D Engineering View), coordinate inputs, jogging, trajectory generator, telemetry readouts, status pills, and live plots.
  - `style.css`: Professional engineering theme, dark/high-contrast modes, responsive layout.
  - `app.js` & `modules/`:
    - `scene.js`: Three.js scene, camera, lights, orbit controls, coordinate axes, dimensions.
    - `robot_view.js`: 3D frame, winches/drums, cables, moving platform, guide rods, target marker, trajectory trail.
    - `engineering_view.js`: Canvas 2D orthographic millimeter projection with dimension annotations, workspace boundary polygon, click-to-target.
    - `telemetry.js`: WebSocket manager with auto-reconnect, packet unpacking, latency monitor.
    - `controls.js`: Move, jog, waypoints, presets, e-stop, speed/accel controls.
    - `plots.js`: Canvas/SVG live time-series plots (position error, cable tensions, motor RPMs, torque).
- `tests/`
  - `test_geometry.py`: Dimensions, symmetry, anchor checks, SI consistency.
  - `test_kinematics.py`: Analytical IK, FK recovery of known poses, analytical vs finite-difference Jacobian, singularity detection.
  - `test_tension.py`: Feasibility checks, non-negative tensions, residual bounds, handling infeasible wrenches.
  - `test_actuator.py`: Spooling equations, speed/torque limits, saturation indicators.
  - `test_trajectory.py`: Straight line, circle, rectangle profiles, intermediate collision & tension violation rejection.
  - `test_simulation.py`: Fixed-step integration, telemetry schema, deterministic step evaluation.
  - `test_api.py`: REST and WebSocket endpoints verification.
- `scripts/`
  - `generate_plots.py`: Offline script using actual solver to generate validation plots (workspace feasibility heatmap, cable lengths vs pose, RPM & tension vs trajectory).
- `docs/`
  - `MODEL.md`: Full physics formulation, coordinates, equations, sign conventions.
  - `ASSUMPTIONS.md`: Assumptions, provisional limits, unverified parameters.
  - `VALIDATION.md`: Test executions, numerical error reports, verification data.
  - `HARDWARE.md`: Engineering notes for physical CDPR hardware construction and motor selection.
- `ros2/`
  - `README.md`, `cdpr_ros2_bridge.py`: Optional ROS 2 node adapter for state/command topic bridging.

## 3. Execution Phases
1. Phase 2: Configuration & Geometry (`robot_config.yaml`, `config.py`, `geometry.py`, `test_geometry.py`).
2. Phase 3: Kinematics (`kinematics.py`, `test_kinematics.py`).
3. Phase 4: Tension Allocation, Actuator & Dynamics (`tension_solver.py`, `actuator.py`, `dynamics.py`, `test_tension.py`, `test_actuator.py`).
4. Phase 5: Collision, Trajectory & Controller (`collision.py`, `trajectory.py`, `controller.py`, `test_trajectory.py`).
5. Phase 6: Simulation Engine & Backend API (`simulation.py`, `state.py`, `routes.py`, `websocket.py`, `main.py`, `test_simulation.py`, `test_api.py`).
6. Phase 7: Frontend Application (`index.html`, `style.css`, Three.js views, 2D engineering canvas, controls, telemetry, live plots).
7. Phase 8: Offline Engineering Validation Scripts & Documentation Generation (`generate_plots.py`, `MODEL.md`, `ASSUMPTIONS.md`, `VALIDATION.md`, `HARDWARE.md`).
8. Phase 9: Optional ROS 2 Bridge & Verification.
9. Phase 10: End-to-end Test Suite Run, UI Verification, Final Report.
