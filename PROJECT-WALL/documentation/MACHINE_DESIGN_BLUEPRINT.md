# PROJECT W.A.L.L. — COMPLETE MACHINE DESIGN BLUEPRINT
## Universal Planar Cable-Driven Autonomous Surface Printing System (CDPR)
**Document Designation:** W.A.L.L.-ENG-CAD-001  
**Revision:** 4.0  
**Classification:** Engineering Specification & Production Blueprint  
**Standard Compliance:** ISO 2768-mK (General Tolerances), DIN 7168, ANSI/RIA R15.06 (Industrial Robot Safety)  
**Applicable Architecture:** 2-DOF 4-Cable Planar Parallel Robot (Part 0 Absolute Design Rules)

---

## 1. SYSTEM KINEMATICS & COORDINATE ARCHITECTURE

PROJECT W.A.L.L. operates strictly as a 2-DOF planar cable-driven parallel robot (CDPR). Four perimeter-mounted winch assemblies ($A_1, A_2, A_3, A_4$) coordinate Dyneema cable lengths to translate a suspended central printing platform across a vertical or inclined planar surface.

```
Coordinate Frame Definition:
Surface Origin (0,0): Lower-Left Corner of Printable Wall Panel
+X Axis: Horizontal to the Right
+Y Axis: Vertical Upward
+Z Axis: Normal out from Wall Surface (Planar Standoff = 2.0 mm)

Anchor Coordinates:
A1 (Upper-Left):  (0.0,   H_wall, Z_offset) = (0.0,   600.0, 28.0) mm
A2 (Upper-Right): (W_wall, H_wall, Z_offset) = (800.0, 600.0, 28.0) mm
A3 (Lower-Left):  (0.0,   0.0,    Z_offset) = (0.0,   0.0,   28.0) mm
A4 (Lower-Right): (W_wall, 0.0,    Z_offset) = (800.0, 0.0,   28.0) mm

Platform Eyelet Attachment Coordinates (Relative to Platform Center B_0):
B1 (Upper-Left):  (-55.0, +42.5, +12.0) mm
B2 (Upper-Right): (+55.0, +42.5, +12.0) mm
B3 (Lower-Left):  (-55.0, -42.5, +12.0) mm
B4 (Lower-Right): (+55.0, -42.5, +12.0) mm
```

---

## 2. NEMA 17 STEPPER WINCH ASSEMBLIES ($A_1 \dots A_4$)

Each of the four corner winch stations is an integrated, self-contained motorized cable mechanism.

```
+-------------------------------------------------------------------------+
|                  NEMA 17 WINCH ASSEMBLY (A1..A4) CAD                    |
+-------------------------------------------------------------------------+
|                                                                         |
|     +-------------------------+                                         |
|     | NEMA 17 STEPPER MOTOR   |                                         |
|     | 42.3 x 42.3 x 40.0 mm   |                                         |
|     | Holding Torque: 0.44 Nm |                                         |
|     | Current: 1.5A / Phase   |                                         |
|     +------------+------------+                                         |
|                  | 5mm D-Shaft                                          |
|                  v                                                      |
|     +------------+------------+                                         |
|     | FLEXIBLE BEAM COUPLER   |                                         |
|     | 19mm OD x 25mm Length   |                                         |
|     +------------+------------+                                         |
|                  | 8mm Precision Ground Stainless Shaft                 |
|                  v                                                      |
|     +------------+------------+   [F688ZZ Flanged Ball Bearing]         |
|     |  LOWER DRUM FLANGE      |   44.0mm OD x 2.5mm Thick (6 Holes)     |
|     +-------------------------+                                         |
|     |  HELICAL GROOVED DRUM   |   28.0mm Root Dia, 22.0mm Width         |
|     |  (Wound Dyneema Spool)  |   Helical Groove Pitch: 1.25mm          |
|     +-------------------------+                                         |
|     |  UPPER DRUM FLANGE      |   44.0mm OD x 2.5mm Thick (6 Holes)     |
|     +------------+------------+                                         |
|                  |                                                      |
|                  v                                                      |
|     +------------+------------+   [F688ZZ Flanged Ball Bearing]         |
|     | OPTICAL ENCODER DISC    |   1000 CPR Quadrature Disc              |
|     +-------------------------+                                         |
|                                                                         |
|     ===> Fairlead Guide Roller: Brass Tangency Pulley (Dia 12.0 mm)    |
|     ===> Corner Mount: 6061-T6 Baseplate + 2x 45mm Vacuum Suction Cups  |
|          + M6 Heavy-Duty Structural Frame Edge Clamp                    |
+-------------------------------------------------------------------------+
```

### 2.1 Stepper Motor Specifications
- **Model:** 17HS4401 (NEMA 17 form factor).
- **Dimensions:** $42.3 \times 42.3 \times 40.0\text{ mm}$ body, $24.0\text{ mm}$ shaft extension.
- **Holding Torque:** $0.44\text{ N}\cdot\text{m}$ ($44\text{ N}\cdot\text{cm}$).
- **Step Angle:** $1.8^\circ$ ($200\text{ full steps/rev}$), driven with $1/16$ microstepping ($3,200\text{ microsteps/rev}$).
- **Phase Current:** $1.5\text{ A DC}$ per phase ($2.8\text{ V}$ rated, $2.4\text{ }\Omega$ resistance, $2.8\text{ mH}$ inductance).
- **Cooling:** 8 longitudinal heatsink flutes machined along stator sides.
- **Locating Boss:** $\varnothing 22.0 \times 2.5\text{ mm}$ pilot boss with 4 tapped M3 holes on $\varnothing 31.0\text{ mm}$ pitch circle.

### 2.2 Motor Wiring Harness Schedule
The motor lead wires exit the rear endcap through a reinforced strain-relief rubber grommet:

| Pin # | Wire Color | Gauge | Signal Name | Motor Phase | Driver Terminal (TMC2209) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Red** | 26 AWG | `M_PHASE_B_POS` | Phase B+ | B1 |
| 2 | **Blue / Yellow** | 26 AWG | `M_PHASE_B_NEG` | Phase B- | B2 |
| 3 | **Green** | 26 AWG | `M_PHASE_A_NEG` | Phase A- | A2 |
| 4 | **Black** | 26 AWG | `M_PHASE_A_POS` | Phase A+ | A1 |

- **Connector Type:** JST-XH 4-pin female socket, $2.50\text{ mm}$ pitch, polarized latching.

### 2.3 Helical Grooved Winch Drum Geometry
- **Material:** CNC Milled 6061-T6 Aluminum, clear anodized.
- **Root Diameter ($D_{\text{root}}$):** $28.00 \pm 0.02\text{ mm}$.
- **Flange Outer Diameter ($D_{\text{flange}}$):** $44.00 \pm 0.05\text{ mm}$.
- **Spooling Width ($W_{\text{spool}}$):** $22.00\text{ mm}$.
- **Flange Lightening:** 6 circumferential $\varnothing 6.5\text{ mm}$ weight-relief holes drilled at $30.0\text{ mm}$ pitch circle.
- **Groove Profile:** Continuous semi-circular helical lathe groove, radius $r_g = 0.65\text{ mm}$ for $1.0\text{ mm}$ cable, pitch $p = 1.25\text{ mm}$ ($17.6\text{ active turns per layer}$).
- **Spooling Capacity per Layer:**
  $$L_{\text{layer 1}} = \pi \cdot (D_{\text{root}} + d_{\text{cable}}) \cdot N_{\text{turns}} = \pi \cdot (28.0 + 1.0) \cdot 17.6 = 1603.5\text{ mm} = 1.60\text{ m}$$
  $$L_{\text{layer 2}} = \pi \cdot (D_{\text{root}} + 3 \cdot d_{\text{cable}}) \cdot N_{\text{turns}} = \pi \cdot (28.0 + 3.0) \cdot 17.6 = 1714.2\text{ mm} = 1.71\text{ m}$$
  Total capacity = $3.31\text{ m}$ (exceeds $1.2\text{ m}$ max cable travel across an $800 \times 600\text{ mm}$ workspace).

---

## 3. DYNEEMA CABLE TRANSMISSION ($C_1 \dots C_4$)

- **Material:** Ultra-High-Molecular-Weight Polyethylene (UHMWPE) — Dyneema® SK78.
- **Braid:** 12-strand hollow single-braid round line.
- **Diameter:** $1.00 \pm 0.05\text{ mm}$.
- **Minimum Tensile Breaking Strength:** $1,400\text{ N}$ ($142\text{ kgf}$).
- **Maximum Permitted Working Load ($T_{\text{max}}$):** $45.0\text{ N}$ (Safety Factor $> 31:1$).
- **Minimum Operating Tension ($T_{\text{min}}$):** $2.5\text{ N}$ (Slack prevention threshold).
- **Nominal Pre-Tension ($T_{\text{nom}}$):** $12.0\text{ N}$.
- **Elastic Modulus ($E$):** $110\text{ GPa}$ ($110,000\text{ N/mm}^2$).
- **Cross-Sectional Area ($A$):** $A = \frac{\pi \cdot d^2}{4} = 0.7854\text{ mm}^2$.
- **Elastic Axial Stiffness ($EA$):**
  $$EA = 110,000 \times 0.7854 = 86,394\text{ N}$$
- **Linear Elastic Elongation:**
  $$\Delta L = \frac{T \cdot L_0}{EA}$$
  At nominal center ($L_0 = 436.0\text{ mm}$, $T = 18.0\text{ N}$):
  $$\Delta L = \frac{18.0 \cdot 436.0}{86,394} = 0.091\text{ mm}$$
  Compensated directly in forward and inverse kinematic solvers.

### 3.1 Cable End Termination & Rigging
1. **Winch Drum Attachment:** Cable end threaded through drum radial entry hole ($\varnothing 1.2\text{ mm}$), secured via a double copper swage sleeve seated in internal counterbore.
2. **Platform Attachment:**
   - Stainless steel teardrop wire-rope thimble (DIN 6899 Form B, size 1.0).
   - Aluminum swage oval sleeve ferrule (DIN 3093 / EN 13411-3), crimped with a calibrated hand tool ($1.5\text{ mm}$ final width).
   - Stainless steel quick-release shackle / clevis pin ($\varnothing 3.0\text{ mm}$) engaging the platform ball-bearing swivel stud.

---

## 4. CENTRAL PRINTING END-EFFECTOR PLATFORM

```
+-------------------------------------------------------------------------+
|                  CENTRAL SUSPENDED PLATFORM (B1..B4)                    |
+-------------------------------------------------------------------------+
|                                                                         |
|   [B1 Swivel Stud]                                    [B2 Swivel Stud]  |
|          \                                                    /         |
|      +----+--------------------------------------------------+----+     |
|      |    |        6061-T6 SKELETAL ALUMINUM BASEPLATE       |    |     |
|      |    |            110.0 x 85.0 x 8.0 mm Chassis         |    |     |
|      |    +--------------------------------------------------+    |     |
|      |    |  [Lightening Pocket]        [Lightening Pocket]  |    |     |
|      |    |      (Mass: 0.28 kg Bare, 0.46 kg Assembled)     |    |     |
|      |    +--------------------------------------------------+    |     |
|      |    |                                                  |    |     |
|      |    |  [POM Ball Standoff 1]     [POM Ball Standoff 2] |    |     |
|      |    |   (-2.0mm to Wall)          (-2.0mm to Wall)     |    |     |
|      |    |                                                  |    |     |
|      |    |  +============================================+  |    |     |
|      |    |  |  DUAL 4mm GROUND GUIDE RODS (SUJ2 STEEL)   |  |    |     |
|      |    |  |  + SINTERED BRONZE BUSHINGS (SAE 841)      |  |    |     |
|      |    |  +============================================+  |    |     |
|      |    |                                                  |    |     |
|      |    |  +--------------------------------------------+  |    |     |
|      |    |  |  1.2N HELICAL COMPLIANCE SPRING (ASTM A228)|  |    |     |
|      |    |  |  7.5 Active Coils, Spring Rate k=0.14 N/mm |  |    |     |
|      |    |  +--------------------------------------------+  |    |     |
|      |    |                                                  |    |     |
|      |    |  +--------------------------------------------+  |    |     |
|      |    |  |  QUICK-RELEASE DOVETAIL SLIDE CARRIAGE     |  |    |     |
|      |    |  |  Brass Knurled M4 Locking Thumbscrew       |  |    |     |
|      |    |  +--------------------------------------------+  |    |     |
|      |    |                         |                        |    |     |
|      |    |                         v                        |    |     |
|      |    |     [MODULE A: PIEZO]   OR   [MODULE B: MARKER]  |    |     |
|      |    |     48-Nozzle Printhead      6mm Chisel Felt Nib |    |     |
|      |    |     FPC Flex Ribbon Bus      Contact Switch      |    |     |
|      |    |     Dual PTFE Ink Lines      Marker Sleeve Clamp |    |     |
|      |    |                                                  |    |     |
|      |    |  [ToF Laser VL53L1X]        [POM Ball Standoff 3]|    |     |
|      |    |  Ranging Sensor             (-2.0mm to Wall)     |    |     |
|      +----+--------------------------------------------------+----+     |
|          /                                                    \         |
|   [B3 Swivel Stud]                                    [B4 Swivel Stud]  |
|                                                                         |
|   ===> Umbilical Arched Flex Bundle: Multi-Conductor Loom + Fluid Lines |
|        Strain-Relief Clamp Bracket at Upper Platform Flange             |
+-------------------------------------------------------------------------+
```

### 4.1 Planar Wall Standoff Mechanism
To guarantee the strict planar constraint without allowing nozzle crash or wall abrasion:
- **Kinematic Standoff:** 3 Delrin (POM) spring-loaded ball transfer units mounted in a stable triangle ($B_{R1} = [-42, 0]$, $B_{R2} = [42, 28]$, $B_{R3} = [42, -28]\text{ mm}$).
- **Ball Material:** $\varnothing 8.0\text{ mm}$ polished AISI 316 stainless steel balls rolling on $\varnothing 1.5\text{ mm}$ internal recirculating balls.
- **Standoff Distance:** Exactly $2.00 \pm 0.05\text{ mm}$ between the aluminum chassis bottom face and the wall plane.
- **Friction Coefficient:** Dynamic rolling friction $\mu_{\text{roll}} \le 0.012$ on primed drywall and smooth wood panels.

---

## 5. PRINTING ACTUATORS & COMPLIANCE SPRING MECHANISM

### 5.1 Z-Axis Floating Compliance Spring
The actuator carriage floats along the Z-axis (normal to the surface) to absorb surface waviness ($\le \pm 2.0\text{ mm}$) while applying a strictly regulated contact force:

- **Spring Standard:** DIN 2095 (Class 1 precision compression springs).
- **Material:** ASTM A228 High-Tensile Music Wire (Spring Steel), shot-peened and oil-tempered.
- **Mean Coil Diameter ($D_m$):** $8.50 \pm 0.10\text{ mm}$.
- **Wire Diameter ($d$):** $1.60 \pm 0.02\text{ mm}$.
- **Total Coils ($n_t$):** 9.5 coils (ends squared and ground flat).
- **Active Coils ($n_a$):** 7.5 coils.
- **Free Length ($L_0$):** $34.00\text{ mm}$.
- **Solid Length ($L_s$):** $15.20\text{ mm}$.
- **Shear Modulus ($G$):** $79.3\text{ GPa}$ ($79,300\text{ N/mm}^2$).
- **Spring Rate ($k$):**
  $$k = \frac{G \cdot d^4}{8 \cdot D_m^3 \cdot n_a} = \frac{79,300 \cdot (1.60)^4}{8 \cdot (8.50)^3 \cdot 7.5} = \frac{520,028}{36,847} = 0.1411\text{ N/mm} = 141.1\text{ N/m}$$
- **Preload Deflection:** $\delta_0 = 8.50\text{ mm}$ (Installed length $L_{\text{installed}} = 25.50\text{ mm}$).
- **Preload Contact Force:**
  $$F_{\text{preload}} = k \cdot \delta_0 = 0.1411 \cdot 8.50 = 1.20\text{ N}$$
- **Operating Force Range:** $0.85\text{ N} \dots 1.55\text{ N}$ across $\pm 2.5\text{ mm}$ wall irregularity.

---

### 5.2 Module A: Drop-on-Demand Micro-Piezo Inkjet Printhead
- **Architecture:** Micro-piezo shear-mode drop-on-demand silicon printhead manifold.
- **Nozzle Configuration:** 48 micro-orifices arranged in 2 parallel staggered columns of 24 nozzles.
- **Nozzle Diameter:** $\varnothing 21.5\text{ }\mu\text{m}$ laser-drilled in gold-coated stainless steel orifice plate.
- **Droplet Volume:** $14.0 \pm 1.5\text{ pL}$ ($14 \times 10^{-12}\text{ Liters}$).
- **Droplet Velocity:** $7.2 \pm 0.8\text{ m/s}$ (traverses $2.0\text{ mm}$ standoff in $0.278\text{ ms}$).
- **Firing Frequency:** Variable $100\text{ Hz} \dots 15.0\text{ kHz}$ per nozzle.
- **Drop Swath Width:** $6.096\text{ mm}$ ($0.240\text{ inches}$ at $100\text{ DPI}$ native nozzle pitch).
- **Ink Feed Lines:** Dual translucent Chemfluor® PTFE tubes ($\varnothing 2.0\text{ mm ID} \times \varnothing 3.2\text{ mm OD}$) with female Luer-lock fittings and anti-backflow duckbill valves.
- **Drive Electronics:** 26-conductor $0.5\text{ mm}$ pitch Flexible Printed Circuit (FPC) ribbon with gold traces carrying high-voltage trapezoidal drive pulses ($0 \dots 28\text{ V}$, $2.5\text{ }\mu\text{s}$ slew rate).

---

### 5.3 Module B: Paint Marker Actuator (Spring-Loaded)
- **Housing:** CNC Milled 6061-T6 Aluminum cylindrical collar sleeve with M16 threaded split collet.
- **Marker Acceptance:** Accommodates standard industrial $\varnothing 15.0\text{ mm} \dots \varnothing 16.5\text{ mm}$ valve-action marker barrels (e.g. Uni Posca PC-5M, Molotow ONE4ALL 127HS).
- **Contact Tip:** $6.0\text{ mm}$ chisel/bullet high-density porous acrylic felt nib.
- **Valve Actuation:** Spring compliance transfers $1.2\text{ N}$ continuous pressure, keeping internal ball valve unseated for uninterrupted ink flow during printing strokes.
- **Contact Feedback:** Omron D2F-01 miniature micro-switch mounted parallel to linear slide; signals supervisory state machine if marker loses contact with wall ($F < 0.3\text{ N}$).

---

## 6. UMBILICAL WIRE HARNESS & FLUID DRAG BLUEPRINT

The umbilical bundle is a flexible, lightweight drag line suspended from the upper wall perimeter, entering the platform through a clamped strain-relief bracket at $(0, +42.5, +34.0)\text{ mm}$.

```
+=============================================================================+
|                 PROJECT W.A.L.L. COMPLETE WIRE & HOSE SCHEDULE              |
+=============================================================================+
| Signal / Conductor Group        | Gauge / Spec   | From       | To          |
+---------------------------------+----------------+------------+-------------+
| Motor M1 4-Lead Stepper Cable   | 4x 26 AWG Cu   | Driver 1   | Motor M1    |
| Motor M2 4-Lead Stepper Cable   | 4x 26 AWG Cu   | Driver 2   | Motor M2    |
| Motor M3 4-Lead Stepper Cable   | 4x 26 AWG Cu   | Driver 3   | Motor M3    |
| Motor M4 4-Lead Stepper Cable   | 4x 26 AWG Cu   | Driver 4   | Motor M4    |
| Encoder E1..E4 Quadrature Lines | 16x 28 AWG Cu  | Encoders   | MCU Timer   |
| ToF Sensor I2C Bus (VCC/GND/SDA/SCL) | 4x 28 AWG Shield| MCU I2C1 | VL53L1X PCB |
| Printhead FPC High-Speed Bus    | 26-Conductor FPC| Pulser PCB| Piezo Head  |
| Marker Contact Micro-Switch     | 2x 28 AWG Cu   | MCU GPIO   | D2F Switch  |
| Ink Supply Line (PTFE Tube)     | 2mm ID / 3.2 OD| Ink Tank   | Piezo/Marker|
| Purge / Flush Fluid Line        | 2mm ID / 3.2 OD| Solenoid   | Printhead   |
| Vacuum Suction Hoses (x2)       | 4mm OD PU Tube | Vac Pump   | Suction Barbs|
| Grounding Braided Strap         | 20 AWG Cu Mesh | Main Frame | EE Chassis  |
+=============================================================================+
```

---

## 7. MANUFACTURING BILL OF MATERIALS (BOM)

| Item # | Part Name | Specification / Drawing | Material | Qty | Fabrication Method |
|:---:|:---|:---|:---|:---:|:---|
| 01 | Motor Stator Unit | 17HS4401 Stepper Motor | Alum / Steel | 4 | Commercial Off-The-Shelf (COTS) |
| 02 | Shaft Coupler | Flexible Helical 5mm to 8mm | 6061-T6 Alum | 4 | COTS |
| 03 | Winch Drum Spool | DWG-WALL-CAD-001 | 6061-T6 Alum | 4 | CNC Lathe + 4-Axis Mill |
| 04 | Drum Flanged Bearing | F688ZZ (8x16x5mm) | Chrome Steel | 8 | COTS |
| 05 | Optical Rotary Encoder | 1000 CPR Quadrature Disc | Optical Resin | 4 | COTS |
| 06 | Fairlead Guide Pulley | DWG-WALL-CAD-002 | Machined Brass | 4 | CNC Swiss Turn |
| 07 | Corner Mounting Bracket | DWG-WALL-CAD-003 | 6061-T6 Alum | 4 | 3-Axis CNC Mill |
| 08 | Vacuum Suction Cup | $\varnothing 45\text{ mm}$ Bellow Cup | Nitrile Rubber | 8 | COTS |
| 09 | Dyneema Cable Line | SK78 12-Strand $\varnothing 1.0\text{ mm}$ | UHMWPE | 4 | Cut to Length ($1.8\text{ m}$) |
| 10 | Cable Thimble | DIN 6899B Size 1.0 | 304 Stainless | 4 | COTS |
| 11 | Swage Oval Sleeve | DIN 3093 Size 1.0 | EN AW-6060 Alum | 8 | COTS (Crimped) |
| 12 | Platform Chassis Plate | DWG-WALL-CAD-004 | 6061-T6 Alum | 1 | 3-Axis CNC Pocketed Mill |
| 13 | Swivel Stud Eyelet | DWG-WALL-CAD-005 | 304 Stainless | 4 | CNC Turn + Pivot Bearing |
| 14 | POM Ball Standoff Unit | $\varnothing 8.0\text{ mm}$ Ball Transfer | POM / SS 316 | 3 | COTS |
| 15 | Linear Compliance Guide Rod | $\varnothing 4.0 \times 48.0\text{ mm}$ Ground Shaft | SUJ2 Hardened | 2 | Precision Ground ($\text{h6}$) |
| 16 | Linear Sintered Bushing | $\varnothing 4\text{ ID} \times \varnothing 8\text{ OD} \times 12\text{ mm}$ | SAE 841 Bronze | 2 | COTS |
| 17 | 1.2N Compliance Spring | DWG-WALL-CAD-006 ($k=0.14\text{ N/mm}$)| ASTM A228 Steel | 1 | Coiled & Ground Ends |
| 18 | Quick-Release Dovetail Slide | DWG-WALL-CAD-007 | 6061-T6 Alum | 1 | CNC Mill |
| 19 | Micro-Piezo Printhead | 48-Nozzle $14\text{ pL}$ Module A | Silicon / Alum | 1 | Custom Sub-Assembly |
| 20 | Paint Marker Sleeve Clamp | DWG-WALL-CAD-008 Module B | 6061-T6 Alum | 1 | CNC Mill |
| 21 | Time-of-Flight Sensor | VL53L1X Breakout | PCB / Glass | 1 | COTS |
| 22 | Umbilical Clamp Bracket | DWG-WALL-CAD-009 | 6061-T6 Alum | 1 | CNC Mill |

---

## 8. GENERAL ASSEMBLY TOLERANCES & GD&T

1. **Linear Tolerances:** ISO 2768-mK ($\pm 0.1\text{ mm}$ for $6-30\text{ mm}$, $\pm 0.2\text{ mm}$ for $30-120\text{ mm}$).
2. **Shaft Fits:**
   - Winch drum bore to shaft: ISO $\text{H7/h6}$ clearance transition fit ($0 \dots +15\text{ }\mu\text{m}$).
   - F688ZZ bearing housing bore: ISO $\text{M7}$ light press fit.
   - Linear guide rod into platform base: ISO $\text{H7/p6}$ interference press fit.
3. **Flatness & Parallelism:**
   - Baseplate mounting surface: Flat within $0.05\text{ mm}$ across $110\text{ mm}$.
   - Dual linear guide rods: Parallel within $0.02\text{ mm}$ across $48\text{ mm}$ span.
4. **Surface Finish:**
   - CNC Milled Aluminum Faces: $Ra \le 1.6\text{ }\mu\text{m}$.
   - Drum Helical Grooves: $Ra \le 0.8\text{ }\mu\text{m}$ (polished to prevent cable fraying).
   - Linear Guide Shafts: $Ra \le 0.2\text{ }\mu\text{m}$ (ground and polished).

---
*Blueprint Approved for Manufacture by Antigravity Engineering Systems Team.*

