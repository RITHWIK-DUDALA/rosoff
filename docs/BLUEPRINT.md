# Engineering Blueprint & Dimensional Specification
## 2-DOF Planar Cable-Driven Parallel Robot (CDPR-2DOF)
**Drawing Number:** `CDPR-DWG-001-REV-B`  
**Standard:** ISO 7200 / ANSI Y14.5  
**Units:** Millimeters [mm] (Calculations in SI: meters [m], kilograms [kg], seconds [s], newtons [N])  
**General Tolerances:** Linear $\pm 0.5\text{ mm}$ | Angular $\pm 0.2^\circ$  
**Material:** 6061-T6 Aluminum Structural Plate / POM Spools / Hardened SUS304 Precision Guide Rods  

---

## 1. Top Orthographic Projection (XY Plane)

```text
 ◄═══════════════════════════════════ 500.0 mm (Frame Width) ══════════════════════════════════►
 ┌──────────────────────────────────────────────────────────────────────────────────────────────┐ ▲
 │ [M1] Anchor C1                                                               [M2] Anchor C2  │ │
 │ (-250.0, +200.0)                                                           (+250.0, +200.0) │ │
 │   (O)═════════════════════════════════════════════════════════════════════════════(O)        │ │
 │    ║ \                                                                         / ║           │ │
 │    ║   \  Cable L1                                                 Cable L2  /   ║           │ │
 │    ║     \                                                                 /     ║           │ │
 │    ║      \    ┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - ┐  /      ║           │ │
 │    ║       \   │   SAFE WORKSPACE ENVELOPE: 360.0 x 280.0 mm           │ /       ║           │ │
 │    ║        \  │   X in [-180, +180], Y in [-140, +140]                │/        ║           │ │
 │════╬═════════\═╡═══════════════════════════════════════════════════════╞═════════╬═══════════│ 120.0 mm
 │[Rod 1: ø10mm] \│   Top Guide Rod (Y = +60.0 mm)                        │[Rod 1]  ║           │ Guide
 │    ║           \               ◄══ 100.0 mm ══►                        │         ║           │ Spacing
 │    ║           │\             ┌────────────────┐                      /│         ║           │ (CTC)
 │    ║           │ \            │ b1 (-50, +40)  │ b2 (+50, +40)       / │         ║           │ │
 │    ║           │  \           │  (•)───────(•) │                    /  │         ║           │ │
 │    ║           │   \          │   │ Platform│  │                   /   │         ║           │ │
 │ ───╬───────────┼────\─────────┼───┼── (0,0) ┼──┼──────────────────/────┼─────────╬───────────│ ▼ 400.0 mm
 │    ║           │     \        │   │  DATUM  │  │ 80.0 mm         /     │         ║           │ (Frame
 │    ║           │      \       │  (•)───────(•) │               /      │         ║           │  Height)
 │    ║           │       \      │ b4 (-50, -40)  │ b3 (+50, -40)        /  │         ║           │ │
 │════╬═══════════╡════════\═════└────────────────┘═════════════════════/═══╡═════════╬═══════════│ │
 │[Rod 2: ø10mm]  │         \    Bottom Guide Rod (Y = -60.0 mm)       /    │[Rod 2]  ║           │ │
 │    ║           │          \                                        /     │         ║           │ │
 │    ║           └ - - - - - \ - - - - - - - - - - - - - - - - - - - - - - ┘       ║           │ │
 │    ║                        \                                    /               ║           │ │
 │    ║  Cable L4               \                                  /     Cable L3   ║           │ │
 │    ║                          \                                /                 ║           │ │
 │   (O)══════════════════════════\══════════════════════════════(O)════════════════(O)         │ │
 │ [M4] Anchor C4                                                               [M3] Anchor C3  │ │
 │ (-250.0, -200.0)                                                           (+250.0, -200.0) │ │
 └──────────────────────────────────────────────────────────────────────────────────────────────┘ ▼
  ◄20mm►                                                                                  ◄20mm►
  Clearance                                                                               Clearance
```

---

## 2. Front Elevation & Section Stack-Up (XZ Plane)

```text
 ◄═══════════════════════════════════ 500.0 mm ════════════════════════════════════════►
 ┌──────────────────────────────────────────────────────────────────────────────────────┐ ▲
 │ [NEMA 17 Stepper Motors]                                  [NEMA 17 Stepper Motors]   │ │
 │ 42 x 42 mm Footprint                                      42 x 42 mm Footprint       │ │
 │ ┌────────────┐                                                          ┌────────────┐│ │ 120.0 mm
 │ │ Spool Drum │══════════════════════════════════════════════════════════│ Spool Drum ││ │ Depth
 │ │  ø 20 mm   │              [Precision Linear Rod: ø 10 mm]             │  ø 20 mm   ││ │ Envelope
 │ └────────────┘         ════════════════════════════════════════         └────────────┘│ │
 │                             ┌────────────────────────┐                                │ │
 │                             │ Moving Platform Plate  │ 6.0 mm Thickness               │ │
 │                             │ 100 x 80 x 6 mm AL6061 │ Mass: 0.50 kg                  │ │
 │                             └────────────────────────┘                                │ │
 │                        [LM10UU Linear Bearing Anti-Rotation]                          │ │
 │ ┌──────────────────────────────────────────────────────────────────────────────────┐ │ │
 │ │ Rigid Structural Subplate / Base Bed Supporting Planar Motion                    │ │ │
 └─┴──────────────────────────────────────────────────────────────────────────────────┴─┴─▼
```

---

## 3. Geometric Coordinates Schedule

### 3.1 Anchor Locations (Global Coordinate Frame Origin at Center $[0, 0]$)

| Channel | Coordinate $[X, Y, Z]\text{ [m]}$ | Coordinate $[X, Y]\text{ [mm]}$ | Position Description | Actuator Channel |
|:---|:---:|:---:|:---|:---|
| **C1** | $[-0.250, +0.200, 0.000]$ | $[-250.0, +200.0]$ | Top-Left Corner Spool | Motor 1 (NEMA 17) |
| **C2** | $[+0.250, +0.200, 0.000]$ | $[+250.0, +200.0]$ | Top-Right Corner Spool | Motor 2 (NEMA 17) |
| **C3** | $[+0.250, -0.200, 0.000]$ | $[+250.0, -200.0]$ | Bottom-Right Corner Spool | Motor 3 (NEMA 17) |
| **C4** | $[-0.250, -0.200, 0.000]$ | $[-250.0, -200.0]$ | Bottom-Left Corner Spool | Motor 4 (NEMA 17) |

### 3.2 Platform Eyelet Attachment Vectors (Relative to Platform Center $P$)

| Attachment | Relative $[b_x, b_y, b_z]\text{ [m]}$ | Relative $[b_x, b_y]\text{ [mm]}$ | Physical Spacing | Fastener |
|:---|:---:|:---:|:---|:---|
| **b1** | $[-0.050, +0.040, 0.000]$ | $[-50.0, +40.0]$ | Top-Left Eyelet | M3 Low-friction Swivel |
| **b2** | $[+0.050, +0.040, 0.000]$ | $[+50.0, +40.0]$ | Top-Right Eyelet | M3 Low-friction Swivel |
| **b3** | $[+0.050, -0.040, 0.000]$ | $[+50.0, -40.0]$ | Bottom-Right Eyelet | M3 Low-friction Swivel |
| **b4** | $[-0.050, -0.040, 0.000]$ | $[-50.0, -40.0]$ | Bottom-Left Eyelet | M3 Low-friction Swivel |

*Platform Attachment Span:* $100.0\text{ mm}$ horizontal $\times 80.0\text{ mm}$ vertical.

---

## 4. Mechanical Subsystem Specifications

### 4.1 Structural Frame
- **Inner Dimensions:** $500.0\text{ mm}$ width $\times 400.0\text{ mm}$ height $\times 120.0\text{ mm}$ depth
- **Material:** 2020 & 2040 Aluminum T-Slot Extrusions with 90° zinc alloy internal brackets and steel gusset plates
- **Base Bed:** 6 mm Cast Acrylic / Aluminum fixture tooling plate providing vertical $+Z$ normal reaction force

### 4.2 End-Effector Carriage Platform
- **Dimensions:** $100.0\text{ mm}$ width $\times 80.0\text{ mm}$ length $\times 6.0\text{ mm}$ plate thickness
- **Mass:** $0.50\text{ kg}$
- **Inertia ($I_{zz}$):** $6.833 \times 10^{-4}\text{ kg}\cdot\text{m}^2$
- **Guide Mechanism:** Dual precision linear ball bushings (LM10UU) running on dual $\varnothing 10.0\text{ mm}$ stainless guide rods spaced $120.0\text{ mm}$ apart, mechanically eliminating rotation ($\theta_z = 0$) and constraining out-of-plane pitch/roll.

### 4.3 Winch Spools & Cables
- **Drum Radius:** $r = 10.0\text{ mm}$ ($\varnothing 20.0\text{ mm}$ drum OD)
- **Groove Pitch:** Helical single-start spool drum with retaining flanges ($32.0\text{ mm}$ flange OD)
- **Cable Material:** UHMWPE (Ultra-High-Molecular-Weight Polyethylene) 8-strand Dyneema
- **Cable Diameter:** $\varnothing 1.0\text{ mm}$
- **Breaking Strength:** $> 900\text{ N}$
- **Simulated Operating Limit:** $T_{\min} = 2.0\text{ N}$, $T_{\max} = 300.0\text{ N}$

### 4.4 Actuators (4x Corner Stepper Motors)
- **Motor Frame:** NEMA 17 ($42.3 \times 42.3\text{ mm}$ faceplate, $31.0\text{ mm}$ bolt pitch circle, M3 threads)
- **Rated Holding Torque:** $0.40\text{ N}\cdot\text{m}$ (Provisional rating)
- **Rated Max Speed:** $300\text{ RPM}$ ($\approx 314.16\text{ mm/s}$ linear cable velocity)
- **Drive Mode:** Closed-loop stepper or geared DC motor with incremental optical/magnetic encoder

---

## 5. Bill of Materials (BOM)

| Item | Component Description | Manufacturer / Part Ref. | Qty | Key Engineering Specs |
|:---:|:---|:---|:---:|:---|
| **1** | 2020 Al T-Slot Extrusions | Misumi HFS5-2020 | 4 | $2\times 500\text{ mm}$, $2\times 400\text{ mm}$ |
| **2** | End-Effector Carriage Plate | Custom CNC Al 6061-T6 | 1 | $100\times 80\times 6\text{ mm}$, Mass: $0.50\text{ kg}$ |
| **3** | NEMA 17 High-Torque Stepper Motors | StepperOnline 17HS19-2004S1 | 4 | $0.40\text{ Nm}$ torque, $300\text{ RPM}$ max |
| **4** | CNC Spool Winch Drums | Custom Delrin/POM Turned | 4 | $\varnothing 20\text{ mm}$ root dia, $r=10\text{ mm}$, M5 setscrew |
| **5** | Dyneema UHMWPE Braided Cord | Dyneema SK75 $\varnothing 1\text{ mm}$ | 4 | $\varnothing 1.0\text{ mm}$, $> 900\text{ N}$ UTS |
| **6** | Hardened Precision Linear Rods | Misumi SFJ10-520 | 2 | $\varnothing 10\text{ mm} \times 520\text{ mm}$, g6 tolerance, SUJ2 |
| **7** | Linear Ball Bearings | THK / LM10UU | 4 | Anti-rotation dual-rod slide blocks |
| **8** | Corner Gusset & Motor Mounting Plates | Al 6061-T6 (Laser Cut 4mm) | 4 | Rigidity corner brackets with NEMA 17 mount |
| **9** | Optical Limit Switches | Omron EE-SX672 | 4 | Homing and boundary overtravel interlocks |

---

## 6. Kinematic & Geometric Formulas

1. **Inverse Kinematics (Cable Vector):**
   $$\mathbf{l}_i = \mathbf{A}_i - (\mathbf{p} + \mathbf{b}_i)$$
   $$L_i = \|\mathbf{l}_i\| = \sqrt{(A_{ix} - p_x - b_{ix})^2 + (A_{iy} - p_y - b_{iy})^2}$$

2. **Cable Unit Direction Vector:**
   $$\mathbf{u}_i = \frac{\mathbf{l}_i}{\|\mathbf{l}_i\|} = \frac{\mathbf{A}_i - (\mathbf{p} + \mathbf{b}_i)}{L_i}$$

3. **Kinematic Structure Matrix ($A^T$):**
   $$A^T = \begin{bmatrix} \mathbf{u}_1 & \mathbf{u}_2 & \mathbf{u}_3 & \mathbf{u}_4 \end{bmatrix}_{2 \times 4}$$

4. **Static Equilibrium Tension Allocation:**
   $$A^T \mathbf{t} + \mathbf{w}_e = \mathbf{0}, \quad \text{where } \mathbf{w}_e = \begin{bmatrix} F_{ext,x} \\ F_{ext,y} \end{bmatrix}$$
   $$\min_{\mathbf{t}} \frac{1}{2} \|\mathbf{t} - \mathbf{t}_0\|^2 \quad \text{s.t.} \quad A^T \mathbf{t} + \mathbf{w}_e = \mathbf{0}, \quad 2.0\text{ N} \le t_i \le 300.0\text{ N}$$
