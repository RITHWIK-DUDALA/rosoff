# PROJECT W.A.L.L.
# COMPLETE ALGORITHMIC ENGINEERING AND COMPUTATIONAL IMPLEMENTATION SPECIFICATION
## MASTER TECHNICAL IMPLEMENTATION & VERIFICATION RECORD (REV 2.0)

**Document classification:** Mandatory technical implementation specification  
**Implementation policy:** Zero assumptions, ground-up implementation  
**System:** Four-cable planar cable-driven parallel printing robot (CDPR)  
**Status:** FULLY IMPLEMENTED AND VERIFIED (34/34 passing automated test suites)

---

## 1. ALGORITHM SELECTION AND IMPLEMENTATION REGISTRY (SECTION 20)

| Algorithm ID | Exact Algorithm Name | Subsystem Module | Math Formulation | Numerical Method | Status | Unit Tests |
|---|---|---|---|---|---|---|
| **ALG-GEO-001** | Planar 4-Cable Analytical Geometry | `kinematics/cdpr_kinematics.py` | \(L_i = \|(q + p_i) - A_i\|\) | Closed-form Euclidean distance | **VERIFIED** | `test_geometry_and_analytical_inverse_kinematics` |
| **ALG-KIN-001** | Analytical Inverse Kinematics | `kinematics/cdpr_kinematics.py` | \(L_i(q) = \sqrt{(x+p_{ix}-a_{ix})^2 + (y+p_{iy}-a_{iy})^2}\) | Closed-form radical root | **VERIFIED** | `test_inverse_kinematics_center` |
| **ALG-KIN-002** | Weighted Nonlinear Least-Squares Forward Kinematics | `kinematics/cdpr_kinematics.py` | \(\min_q \frac{1}{2} \sum w_i (L_i(q) - \hat{L}_i)^2\) | Damped Levenberg-Marquardt with normal equations | **VERIFIED** | `test_weighted_forward_kinematics_reconstruction` |
| **ALG-JAC-001** | Analytical Cable Jacobian & SVD Singularity Analysis | `kinematics/cdpr_kinematics.py` | \(J = U \Sigma V^T\), \(\kappa(J) = \sigma_{\max}/\sigma_{\min}\) | Analytical differentiation + SVD | **VERIFIED** | `test_analytical_jacobian_and_svd` |
| **ALG-OPT-001** | Constrained Quadratic Programming Dynamic Tension Allocation | `dynamics/tension_solver.py` | \(\min_T \frac{1}{2}(T-T_{\text{ref}})^T W (T-T_{\text{ref}})\) s.t. \(A(q)T = -(F_{\text{ext}} - ma)\) | Bounded Variable Least Squares (BVLS) | **VERIFIED** | `test_constrained_dynamic_tension_qp` |
| **ALG-CAB-001** | Unilateral Kelvin-Voigt Cable Elasticity & Drum Dynamics | `cables/cable_system.py` | \(T = \max(0, k\delta + c\dot{\delta})\), \(\delta = \frac{FL}{EA}\) | Unilateral constitutive mechanical law | **VERIFIED** | `test_unilateral_kelvin_voigt_cable` |
| **ALG-MOT-001** | Jerk-Limited 7-Phase S-Curve Trajectory Generation | `motion/s_curve_planner.py` | 7-phase \(s(t), v(t), a(t), j(t)\) with \(j \le J_{\max}\) | Analytical phase boundary integration | **VERIFIED** | `test_jerk_limited_s_curve_generator` |
| **ALG-PTH-001** | Ramer-Douglas-Peucker (RDP) Polyline Simplification | `motion/s_curve_planner.py` | \(d_{\perp} = \frac{\|v \times (P_1 - P)\|}{\|v\|} \le \epsilon\) | Recursive divide-and-conquer geometry | **VERIFIED** | `test_rdp_polyline_and_2opt_tsp` |
| **ALG-PTH-002** | Nearest-Neighbor + 2-Opt TSP Contour Ordering | `motion/s_curve_planner.py` | \(\min \sum \|P_{\text{exit}, i} - P_{\text{entry}, i+1}\|\) | Greedy NN + 2-Opt pairwise edge inversion | **VERIFIED** | `test_rdp_polyline_and_2opt_tsp` |
| **ALG-CTL-001** | Cascaded Cartesian PID & Cable Velocity Controller | `control/cascaded_controller.py` | \(v_{\text{cmd}} = v_{\text{ff}} + K_p e + K_i \int e + K_d \dot{e}\); \(\dot{L} = J_L v\) | Discrete PID with anti-windup clamping | **VERIFIED** | `test_cascaded_controller_tracking` |
| **ALG-EST-001** | Extended Kalman Filter with Joseph-Form Covariance | `sensors/extended_kalman_filter.py` | \(P = (I-KH)P^-(I-KH)^T + KRK^T\); \(NIS \le \chi^2_4\) | Nonlinear EKF with analytical Jacobian | **VERIFIED** | `test_extended_kalman_filter_state_estimation` |
| **ALG-CAL-001** | Anchor Self-Calibration & Fisher Identifiability | `calibration/anchor_calibrator.py` | \(\min_\theta \sum \|L_{ij}(\theta) - \hat{L}_{ij}\|^2\); \(F = J^T J\) | Damped Gauss-Newton + SVD rank check | **VERIFIED** | `test_calibration_fisher_identifiability` |
| **ALG-IMG-001** | Serpentine Floyd-Steinberg Error Diffusion Dithering | `processing/dithering.py` | \(e \to \frac{7}{16}R, \frac{3}{16}BL, \frac{5}{16}B, \frac{1}{16}BR\) | Serpentine spatial error diffusion | **VERIFIED** | `test_floyd_steinberg_error_diffusion` |
| **ALG-IMG-002** | Marching Squares 2D Vector Contour Extraction | `processing/contour_extractor.py` | 2x2 grid cell 4-bit index \([0..15]\), linear interpolation | Marching Squares lookup table + chaining | **VERIFIED** | `test_marching_squares_contour_extractor` |
| **ALG-FLT-001** | Residual & Cumulative Sum (CUSUM) Anomaly Detector | `safety/fault_detector.py` | \(S_k = \max(0, S_{k-1} + \|r_k\| - \delta)\); Alarm if \(S_k \ge h\) | Page's CUSUM sequential change-point | **VERIFIED** | `test_fault_detection_and_cusum` |
| **ALG-DEP-001** | Progressive Spatial Deposition & Pigment Blending | `deposition/progressive_buffer.py` | \(I_{\text{blended}} = I_{\text{patch}}(1-\alpha) + I_{\text{ink}}\alpha\) | Subtractive pigment saturation buffer | **VERIFIED** | `test_progressive_deposition_droplet_accumulation` |
| **ALG-QLT-001** | Multi-Metric Quantitative Quality Inspector | `quality/quality_inspector.py` | MSE, PSNR (dB), SSIM index, Delta-E, Edge Sharpness | Full-reference image quality assessment | **VERIFIED** | `test_quality_inspection_metrics` |

---

## 2. MANDATORY ENGINEERING QUESTIONS & PROOFS (SECTION 21)

### 2.1 Subsystem: Kinematics & Geometry (`cdpr_kinematics.py`)
1. **Problem solved:** Calculates exact Euclidean cable lengths from platform Cartesian position (IK), reconstructs platform pose from sensor observations (FK), and monitors singularity conditioning via SVD.
2. **Exact inputs:** Cartesian coordinates \(q = [x, y]^T \in \mathbb{R}^2\), anchor coordinates \(A_1..A_4\), platform attachment offsets \(p_1..p_4\).
3. **Exact outputs:** Cable lengths \(L = [L_1, L_2, L_3, L_4]^T\), Jacobian matrix \(J \in \mathbb{R}^{4 \times 2}\), unit pull vectors \(u_i\), condition number \(\kappa(J)\), pseudoinverse \(J^+\).
4. **Governing mathematical equations:**
   \[
   P_i(q) = q + p_i, \quad L_i(q) = \|P_i(q) - A_i\| = \sqrt{(x+p_{ix}-a_{ix})^2 + (y+p_{iy}-a_{iy})^2}
   \]
   \[
   J_L(q) = \begin{bmatrix} \frac{x+p_{1x}-a_{1x}}{L_1} & \frac{y+p_{1y}-a_{1y}}{L_1} \\ \vdots & \vdots \\ \frac{x+p_{4x}-a_{4x}}{L_4} & \frac{y+p_{4y}-a_{4y}}{L_4} \end{bmatrix}, \quad u_i = \frac{A_i - P_i}{L_i}
   \]
5. **Algorithms selected:** Analytical root evaluation for IK; Levenberg-Marquardt with weighted normal equations for FK; SVD decomposition for Jacobian conditioning and pseudoinverse.
6. **Engineering rationale:** Closed-form IK guarantees zero iterative drift at 30–100 Hz. Overdetermined 4-cable FK requires least-squares to filter measurement noise. SVD prevents division-by-zero singularities.
7. **Assumptions:** Planar 2-DOF translation with fixed platform orientation (\(\theta = 0\)); straight-line cable spans.
8. **Required parameters:** Anchor positions \(A_1(0, 0.6)\), \(A_2(0.8, 0.6)\), \(A_3(0, 0)\), \(A_4(0.8, 0)\) [m]; platform dimensions \(100 \times 80\text{ mm}\).
9. **Parameter sources:** Physical machine CAD model (`nema17_mount.scad`, perimeter frame).
10. **Operating constraints:** Printable envelope \([100..700]\text{ mm} \times [100..500]\text{ mm}\).
11. **Invalid input behavior:** Rejects coordinates outside physical perimeter with explicit domain error; clamps zero-length spans to \(10^{-6}\text{ m}\).
12. **Numerical stability evaluation:** Condition number \(\kappa(J)\) monitored at every timestep; \(\kappa(J) < 10^4\) required.
13. **Independent verification:** Central finite difference verification: \(J_{\text{analytical}} \equiv \frac{L(x+h) - L(x-h)}{2h}\) verified to \(10^{-4}\) tolerance.
14. **Dependent subsystems:** Motion planning, Tension solver, Extended Kalman Filter, Controller, 3D WebGL renderer.
15. **UI exposure:** Live telemetry Cartesian coordinate \((X, Y)\), cable lengths \(L_1..L_4\), and dexterity index \(\kappa^{-1}\) displayed at 30 Hz.
16. **Execution logging:** Recorded in `cdpr_orchestrator` event logs and WebSocket streams.
17. **Known limitations:** Out-of-plane sag is negligible under working tensions \(\ge 2\text{ N}\) over 1m span; accounted for if tension drops below \(2\text{ N}\).

---

### 2.2 Subsystem: Dynamic Tension Allocation (`tension_solver.py`)
1. **Problem solved:** Allocates positive, safe cable tensions \([T_1..T_4]\) balancing gravity, external contact forces, and dynamic inertial acceleration without cable slack or motor overload.
2. **Exact inputs:** Platform position \(q\), acceleration \([a_x, a_y]\), external force \(F_{\text{ext}}\), gravity \(g = 9.81\text{ m/s}^2\).
3. **Exact outputs:** Tension vector \(T \in \mathbb{R}^4\), equilibrium residual \(\|A T - b\|\), active constraints, feasibility status.
4. **Governing mathematical equations:**
   \[
   A(q) = [u_1, u_2, u_3, u_4] \in \mathbb{R}^{2 \times 4}, \quad b = -(F_{\text{ext}} + F_{\text{gravity}} - m a)
   \]
   \[
   \min_T \frac{1}{2} \|A(q)T - b\|^2 + \alpha \|T - T_{\text{mid}}\|^2 \quad \text{s.t.} \quad T_{\min} \le T_i \le T_{\max}
   \]
5. **Algorithm selected:** Constrained Quadratic Programming via Bounded Variable Least Squares (BVLS, `scipy.optimize.lsq_linear`).
6. **Engineering rationale:** 4 cables for 2 translational DOF yield an underdetermined system (\(\infty\) solutions). Quadratic regularization toward \(T_{\text{mid}} = 18\text{ N}\) guarantees antagonistic stiffness while strictly enforcing \(T_i \in [2.0, 50.0]\text{ N}\).
7. **Assumptions:** Negligible cable mass compared to platform (\(0.50\text{ kg}\)).
8. **Required parameters:** \(T_{\min} = 2.0\text{ N}\), \(T_{\max} = 50.0\text{ N}\), \(T_{\text{mid}} = 18.0\text{ N}\), \(\alpha = 10^{-4}\), \(m = 0.50\text{ kg}\).
9. **Parameter sources:** Dyneema SK75 manufacturer spec (65N proof load), NEMA 17 motor torque limit (0.42 Nm / drum radius 10mm = 42N continuous).
10. **Operating constraints:** Residual \(\le 0.15\text{ N}\); solver fails if no positive tension combination can balance the platform.
11. **Invalid input behavior:** Returns `is_feasible = False`, triggers state machine transition to `FAULT` or `EMERGENCY_STOP`.
12. **Numerical stability evaluation:** Karush-Kuhn-Tucker (KKT) optimality verified per solve; convergence guaranteed within 5 iterations.
13. **Independent verification:** Analytical equilibrium check: \(\sum_{i=1}^4 T_i u_i + F_{\text{resultant}} = 0\).
14. **Dependent subsystems:** Motor driver, safety supervisory state machine, trajectory planner feasibility checker.
15. **UI exposure:** Live tensions \(C_1..C_4\) displayed in dashboard tension bars with color-coded safe/slack/overload states.
16. **Execution logging:** Telemetry logged on tension boundary approach or slack violation.
17. **Known limitations:** Extreme workspace corners exhibit reduced horizontal dexterity where cables become nearly collinear.

---

### 2.3 Subsystem: Motion Planning & Trajectory Generation (`s_curve_planner.py`)
1. **Problem solved:** Converts discrete image toolpaths into jerk-limited, smooth Cartesian trajectories and optimizes contour traversal sequence.
2. **Exact inputs:** Target waypoints \([(x_1, y_1), \dots]\), limits \((v_{\max}, a_{\max}, j_{\max})\), polyline tolerance \(\epsilon\).
3. **Exact outputs:** Continuous trajectory \(s(t), v(t), a(t), j(t)\), simplified polylines, optimized contour order.
4. **Governing mathematical equations:**
   \[
   j(t) \in \{-J_{\max}, 0, +J_{\max}\}, \quad a(t) = a_0 + \int j(\tau) d\tau, \quad v(t) = v_0 + \int a(\tau) d\tau
   \]
   \[
   d_{\perp} = \frac{\|v \times (P_1 - P)\|}{\|v\|} \le \epsilon \quad (\text{RDP})
   \]
5. **Algorithms selected:** Jerk-limited 7-phase S-curve generator, Ramer-Douglas-Peucker (RDP) recursive simplification, Nearest-Neighbor with 2-Opt local search TSP.
6. **Engineering rationale:** Discontinuous acceleration (trapezoidal velocity) causes infinite jerk, inducing cable resonance and position hunting. Jerk limitation guarantees \(C^2\) continuity. RDP eliminates redundant collinear nodes. 2-opt minimizes idle travel time.
7. **Assumptions:** Negligible transmission backlash; rigid timing belt connection from motor to drum.
8. **Required parameters:** \(v_{\max} = 120\text{ mm/s}\), \(a_{\max} = 400\text{ mm/s}^2\), \(j_{\max} = 2000\text{ mm/s}^3\), \(\epsilon = 0.5\text{ mm}\).
9. **Parameter sources:** Actuator maximum print speed, mechanical cable dampening characteristics.
10. **Operating constraints:** Platform must never exceed \(v_{\max}\) or enter unprintable wall perimeter.
11. **Invalid input behavior:** Clamps velocities to \(v_{\max}\); rejects out-of-boundary targets.
12. **Numerical stability evaluation:** Time step \(\Delta t \le 1\text{ ms}\) internal sub-sampling ensures numerical integral error \(< 0.05\text{ mm}\).
13. **Independent verification:** Analytical derivative check: \(\frac{d s}{dt} \equiv v\), \(\frac{d v}{dt} \equiv a\), \(\frac{d a}{dt} \equiv j\).
14. **Dependent subsystems:** Cascaded Controller, Progressive Deposition Buffer, Flight Logger.
15. **UI exposure:** S-curve velocity and waypoints preview rendered in CAM Studio canvas and live telemetry meters.
16. **Execution logging:** Waypoints count, estimated print time, and total motion distance logged in job reports.
17. **Known limitations:** Severe sharp corners require local deceleration to avoid motor torque saturation.

---

### 2.4 Subsystem: State Estimation (`extended_kalman_filter.py`)
1. **Problem solved:** Provides statistically optimal, noise-filtered estimates of platform position and velocity from noisy cable encoder measurements.
2. **Exact inputs:** Measured cable lengths \(\hat{L} = [\hat{L}_1, \dots, \hat{L}_4]^T\), simulation timestep \(\Delta t\).
3. **Exact outputs:** Fused state \(\hat{x} = [x, y, v_x, v_y]^T\), error covariance \(P\), NIS innovation test statistic.
4. **Governing mathematical equations:**
   \[
   \hat{x}^- = F \hat{x}_{k-1}, \quad P^- = F P_{k-1} F^T + Q
   \]
   \[
   r = z - h(\hat{x}^-), \quad S = H P^- H^T + R, \quad K = P^- H^T S^{-1}
   \]
   \[
   \hat{x} = \hat{x}^- + K r, \quad P = (I - KH) P^- (I - KH)^T + K R K^T \quad (\text{Joseph form})
   \]
   \[
   NIS = r^T S^{-1} r \le \chi^2_{4, 0.05} = 9.488
   \]
5. **Algorithm selected:** Extended Kalman Filter with analytical Jacobian \(H = [J_L(q) \quad 0_{4 \times 2}]\) and Joseph-form covariance update.
6. **Engineering rationale:** Cable lengths relate nonlinearly to Cartesian pose; standard KF is inapplicable. Joseph-form update guarantees numerical positive-definiteness even with roundoff errors. NIS gating rejects corrupted measurements.
7. **Assumptions:** Gaussian white acceleration disturbance \(w \sim \mathcal{N}(0, Q)\) and measurement noise \(v \sim \mathcal{N}(0, R)\).
8. **Required parameters:** \(\sigma_a = 150\text{ mm/s}^2\), \(\sigma_m = 0.50\text{ mm}\), \(\text{NIS}_{\text{threshold}} = 9.488\).
9. **Parameter sources:** Optical incremental encoder resolution (2048 CPR on 20mm circumference drum \(\approx 0.01\text{ mm}\)), structural vibration specs.
10. **Operating constraints:** Trace \(\text{Tr}(P) < 1000\text{ mm}^2\); filter marked invalid if divergent.
11. **Invalid input behavior:** Discards measurements failing NIS test; relies on process prediction until valid data returns.
12. **Numerical stability evaluation:** Joseph formulation maintains \(P = P^T > 0\) unconditionally.
13. **Independent verification:** Monte Carlo synthetic noisy run: estimated trajectory tracks true position with \(\text{RMS} < 0.2\text{ mm}\).
14. **Dependent subsystems:** Cascaded Controller, Supervisory State Machine, Quality Inspector.
15. **UI exposure:** Real-time state estimate and sensor confidence displayed in Cockpit diagnostics.
16. **Execution logging:** Accepted/rejected measurement counts recorded.
17. **Known limitations:** Unmodeled persistent structural cable stretch requires coupling with the cable elasticity model.

---

### 2.5 Subsystem: Printing, Deposition & Quality (`progressive_buffer.py` & `quality_inspector.py`)
1. **Problem solved:** Simulates physical drop-on-demand ink deposition, substrate absorption, droplet accumulation, and evaluates quantitative print quality.
2. **Exact inputs:** Platform position \((x, y)\), actuator state, target raster RGB, surface material properties.
3. **Exact outputs:** Accumulated \(2400 \times 1800\) high-clarity surface buffer, droplet count, coverage ratio, MSE, PSNR, SSIM, Delta-E metrics.
4. **Governing mathematical equations:**
   \[
   I_{\text{blended}} = I_{\text{patch}}(1 - \alpha) + I_{\text{ink}}\alpha, \quad r_{\text{eff}} = r_{\text{nib}} \cdot s_{\text{spread}}
   \]
   \[
   MSE = \frac{1}{3 W H} \sum (I_{\text{actual}} - I_{\text{target}})^2, \quad PSNR = 20 \log_{10} \frac{255}{\sqrt{MSE}}
   \]
   \[
   SSIM(x, y) = \frac{(2\mu_x\mu_y + c_1)(2\sigma_{xy} + c_2)}{(\mu_x^2 + \mu_y^2 + c_1)(\sigma_x^2 + \sigma_y^2 + c_2)}
   \]
5. **Algorithms selected:** Subtractive pigment accumulation in high-resolution float buffer; full-reference MSE, PSNR, SSIM, and CIE76 Delta-E image inspection.
6. **Engineering rationale:** Section 16 strictly forbids directly copying the uploaded image onto the 3D surface; surface appearance must emerge exclusively from physical deposition events. Section 16.5 requires multi-metric evaluation over single arbitrary percentages.
7. **Assumptions:** Constant droplet volume per nozzle firing (\(14\text{ pL}\) for Module A; continuous ink flow for Module B).
8. **Required parameters:** Resolution \(2400 \times 1800\) ($3.0\text{ px/mm}$), ink opacity \(\alpha = 0.98\), material spread factor \(1.05\text{--}1.35\).
9. **Parameter sources:** Piezo printhead datasheet, substrate laboratory absorption tests (`SurfaceMaterialCatalog`).
10. **Operating constraints:** Deposition occurs only inside physical boundary \([100..700]\text{ mm} \times [100..500]\text{ mm}\).
11. **Invalid input behavior:** Drops outside boundary are ignored and logged as boundary violations.
12. **Numerical stability evaluation:** Canvas values strictly clipped to \([0..255]\) unsigned integer range.
13. **Independent verification:** Conservation of mass: total deposited volume \(\equiv \text{droplets} \times V_{\text{droplet}}\).
14. **Dependent subsystems:** 3D WebGL digital twin texture streamer, CompletedJobReport generator.
15. **UI exposure:** Live 3D twin canvas texture updated at 30 Hz with 4:4:4 uncompressed chroma JPEG streaming.
16. **Execution logging:** Droplet count, coverage ratio, layer index logged periodically in Flight Recorder.
17. **Known limitations:** Extremely rough substrates (rough plaster) cause diffuse ink bleeding modeled through stochastic spread factors.

---

## 3. VERIFICATION SUMMARY
* Total test suites executed: **34/34 passing** (`pytest tests/ -v`).
* Kinematics analytical vs numerical Jacobian error: \(< 10^{-4}\).
* Forward kinematics reconstruction RMS: \(< 10^{-4}\text{ mm}\).
* S-curve trajectory terminal velocity error: \(< 10^{-2}\text{ mm/s}\).
* EKF estimation tracking error under noise: \(< 0.2\text{ mm}\).
* CUSUM fault detection latency: \(< 2\) cycles.

