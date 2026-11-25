# PROJECT W.A.L.L. — Robotic Surface Printer & Hyper-Actuator Application

**Project Name:** PROJECT W.A.L.L.  
**System Architecture:** Planar Cable-Driven Surface Printer + Novel Active UV-Piezo End-Effector  
**Application Type:** Standalone Interactive Digital Twin & Control Application  

---

## 1. Overview

**PROJECT W.A.L.L.** is an independent robotic application suite developed for vertical architectural surface printing. It integrates a 4-cable planar robot kinematic digital twin with a novel non-contact dual-stage active UV-piezo printing actuator (HYPER-ACTUATOR Mk-1) and industrial UV inkjet modeling.

### Key Capabilities:
- **Interactive 3D Digital Twin:** Real-time WebGL (Three.js) viewport with forward kinematics state estimation and cable tension visualization.
- **Novel Printing End-Effector Studio:** Dedicated CAD, physics, and droplet simulation laboratory for active non-contact wall printing actuators.
- **UVWALL-600 Digital Twin:** Real-time 3D simulation of a dual-axis vertical industrial UV wall printer with genuine Epson I3200 micro-piezo drop-on-demand firing, trailing 395 nm UV curing, and live ink deposition onto wall canvases.
- **CAM Image Processor:** Digital artwork rasterizer, path planner, and G-code / trajectory generator.
- **Parametric OpenSCAD Models:** 3D printable mechanical parts for end-effector chassis, UV curing wings, and nozzle arrays.

---

## 2. Directory Structure

```text
PROJECT-WALL/
├── backend/                  # Python FastAPI simulation & kinematics server
│   ├── app/
│   │   ├── kinematics/       # Analytical inverse/forward kinematics solvers
│   │   ├── motion/           # Trajectory planning & motion profiling
│   │   ├── perception/       # Wall distance tracking & collision detection
│   │   └── simulation/       # Multi-body physics & cable tension allocation
│   ├── main.py               # FastAPI entry point (WebSocket + REST on port 8000)
│   └── run_backend.py        # Standalone launcher
│
├── frontend/                 # Interactive browser application
│   ├── index.html            # Main robotic cable printer cockpit
│   ├── actuator.html         # HYPER-ACTUATOR Mk-1 Innovation & Physics Studio
│   ├── uvwall600.html        # UVWALL-600 Live Printing Process & Digital Twin
│   ├── blueprint.html        # Architectural 2D dimensioned blueprints
│   ├── processor.html        # Image CAM processor & trajectory planner
│   ├── recipe.html           # Paint formulation & BOM calculator
│   ├── drawings/             # 14 ISO 128 production engineering SVG blueprints
│   ├── libs/                 # Three.js and OrbitControls
│   └── package.json          # Frontend server configuration
│
├── cad/                      # Parametric mechanical design models
│   └── novel_actuator_system/
│       ├── hyper_actuator_standalone.scad
│       ├── uv_pinning_wing.scad
│       └── view_all_stls.scad
│
├── documentation/            # Architectural research & design records
├── scripts/                  # Calibration, simulation & utility scripts
└── tests/                    # End-to-end integration & kinematics test suites
```

---

## 3. Quickstart & Running the Application

### 3.1 Backend Simulation Service (Port 8000)
Requirements: Python 3.10+ with `numpy`, `scipy`, `fastapi`, `uvicorn`.

```bash
cd backend
python -u main.py
```
* Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
* WebSocket Telemetry Stream: `ws://localhost:8000/ws/telemetry`

### 3.2 Frontend Studio (Port 3000)
Requirements: Node.js (with `npx` or `http-server`).

```bash
cd frontend
npx --yes http-server . -p 3000 -c-1
```
* **Cockpit:** [http://localhost:3000/index.html](http://localhost:3000/index.html)
* **Hyper-Actuator Studio:** [http://localhost:3000/actuator.html](http://localhost:3000/actuator.html)
* **UVWALL-600 Studio:** [http://localhost:3000/uvwall600.html](http://localhost:3000/uvwall600.html)

---

## 4. Engineering Standards & Tolerances
- **Mechanical Tolerances:** ISO 2768-mK
- **Drawings Standard:** ISO 128 First-Angle Projection
- **Coordinate Conventions:** Cartesian Upright (X: Horizontal Scan, Y: Elevation/Z-Up, Z: Stand-off to Wall)
