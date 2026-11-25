# PROJECT W.A.L.L. — System Architecture Specification
## Universal Planar Cable-Driven Autonomous Surface Printing System

### 1. Architectural Philosophy
PROJECT W.A.L.L. is engineered as a portable, four-cable, planar parallel robot (Cable-Driven Parallel Robot / CDPR) specifically designed for autonomous reproduction of digital artwork on vertical and inclined planar surfaces.

In strict compliance with the **Part 0 Absolute Design Rules**, the system rejects:
- Wheeled floor navigation
- Differential-drive chassis
- Robotic arms or conventional gantries
- Instant image texture assignment
- Undocumented physical assumptions

### 2. High-Level Subsystem Breakdown
```
+-----------------------------------------------------------------------------------+
|                            PROJECT W.A.L.L. DIGITAL TWIN                          |
+-----------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
        v                                                                   v
+-----------------------------+                           +---------------------------------+
|       BACKEND ENGINE        |                           |       FRONTEND COCKPIT          |
| (Python 3.11, FastAPI, SciPy)|                          | (HTML5, ES Modules, Three.js)   |
+-----------------------------+                           +---------------------------------+
| • CDPROrchestrator          |                           | • 3D Digital Twin Viewport      |
| • Kinematics (IK & FK)      | <==== WebSocket 30Hz ===> | • 2D Dimensioned Blueprint View |
| • Bounded QP Tension Solver |                           | • Real-time Strip Charts        |
| • 4 Winch Motor Models      |                           | • Digital Artwork Studio        |
| • Dyneema Cable System      |                           | • Quality Inspection Report     |
| • Progressive Buffer Canvas |                           | • Scenarios 1-12 Control Pad    |
| • Supervisory State Machine |                           | • E-STOP & Reset Interlocks     |
+-----------------------------+                           +---------------------------------+
```

### 3. Coordinate System & Geometry
- **Origin $(0, 0)$**: Bottom-left corner of the mounting surface.
- **+X Axis**: Extends horizontally to the right across the surface.
- **+Y Axis**: Extends vertically upward along the surface.
- **Anchors**:
  - $A_1$: Upper-Left $(0, H)$
  - $A_2$: Upper-Right $(W, H)$
  - $A_3$: Lower-Left $(0, 0)$
  - $A_4$: Lower-Right $(W, 0)$
- **Central Platform**: Suspended 2-DOF chassis $(100 \times 80\text{ mm})$ with attachment eyelets $B_1, B_2, B_3, B_4$.

