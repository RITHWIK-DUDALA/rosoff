"""
Authoritative Algorithm Implementation Registry for PROJECT W.A.L.L.
Codifies all algorithms specified in Sections 1-22 of the Engineering Specification.
Every record contains the 16 mandatory properties required by Section 1.1.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class AlgorithmRecord:
    algorithm_id: str
    name: str
    module: str
    version: str
    purpose: str
    engineering_rationale: str
    inputs: str
    outputs: str
    mathematical_formulation: str
    parameters: str
    parameter_units: str
    numerical_method: str
    convergence_conditions: str
    failure_conditions: str
    computational_complexity: str
    execution_frequency: str
    subsystem_integration: str
    unit_tests: str
    independent_validation: str
    status: str = "IMPLEMENTED_AND_VERIFIED"


class AlgorithmRegistry:
    def __init__(self):
        self._registry: Dict[str, AlgorithmRecord] = {}
        self._populate_baseline_registry()

    def register(self, record: AlgorithmRecord):
        self._registry[record.algorithm_id] = record

    def get_all(self) -> List[Dict[str, Any]]:
        return [asdict(r) for r in self._registry.values()]

    def get_by_id(self, alg_id: str) -> Optional[AlgorithmRecord]:
        return self._registry.get(alg_id)

    def _populate_baseline_registry(self):
        records = [
            AlgorithmRecord(
                algorithm_id="ALG-GEO-001",
                name="Planar 4-Cable Analytical Geometry",
                module="backend/app/kinematics/cdpr_kinematics.py",
                version="2.0.0",
                purpose="Calculate global attachment points and Euclidean cable spans",
                engineering_rationale="Analytical closed-form model eliminates approximation errors in base coordinates",
                inputs="q = [x, y]^T (m or mm)",
                outputs="P_i = q + p_i (attachment points), L_i = ||P_i - A_i||",
                mathematical_formulation="L_i(q) = sqrt((x + p_ix - a_ix)^2 + (y + p_iy - a_iy)^2)",
                parameters="A_i (anchor positions), p_i (platform offset vectors)",
                parameter_units="meters (internal), mm (readout)",
                numerical_method="Analytical Euclidean distance",
                convergence_conditions="Instantaneous analytical evaluation",
                failure_conditions="Geometric degeneracy: attachment coincides with anchor (L_i <= 0)",
                computational_complexity="O(1) constant time (4 cables)",
                execution_frequency="30 Hz simulation clock & per trajectory step",
                subsystem_integration="Feeds IK, FK, Jacobian, Trajectory, and Tension solver",
                unit_tests="tests/unit/test_cdpr_kinematics.py::test_inverse_kinematics_center",
                independent_validation="Independent CAD coordinate verification from OpenSCAD model"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-KIN-001",
                name="Analytical Inverse Kinematics",
                module="backend/app/kinematics/cdpr_kinematics.py",
                version="2.0.0",
                purpose="Determine exact cable lengths for any commanded Cartesian pose",
                engineering_rationale="Direct analytical mapping without iterative drift or lag",
                inputs="Platform Cartesian position (x, y)",
                outputs="Cable lengths vector L = [L1, L2, L3, L4]^T",
                mathematical_formulation="L_i = ||(q + p_i) - A_i||",
                parameters="Anchors A1..A4, Platform dimensions (w=100mm, h=80mm)",
                parameter_units="mm (user interface), m (internal physics)",
                numerical_method="Closed-form quadratic root",
                convergence_conditions="Analytical (1 step)",
                failure_conditions="Coordinate outside geometric envelope",
                computational_complexity="O(1)",
                execution_frequency="30 Hz - 100 Hz",
                subsystem_integration="Feeds motor spool commands and trajectory interpolator",
                unit_tests="tests/unit/test_cdpr_kinematics.py::test_inverse_kinematics_center",
                independent_validation="Pythagorean theorem verification on reference grid"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-KIN-002",
                name="Weighted Nonlinear Least-Squares Forward Kinematics",
                module="backend/app/kinematics/cdpr_kinematics.py",
                version="2.0.0",
                purpose="Reconstruct platform Cartesian pose from 4 measured cable lengths",
                engineering_rationale="Resolves redundant overdetermined 4-cable observation with sensor noise weighting",
                inputs="Measured lengths L_hat = [L1..L4], weights w = [w1..w4], initial guess q_0",
                outputs="Estimated pose q = [x, y]^T, RMS residual error (mm), diagnostics",
                mathematical_formulation="min_q 0.5 * sum_i w_i * (L_i(q) - L_hat_i)^2",
                parameters="Observation covariance / confidence weights w_i, damping factor lambda=0.01",
                parameter_units="weights: dimensionless (1/mm^2), lengths: mm",
                numerical_method="Damped Gauss-Newton / Levenberg-Marquardt with normal equations",
                convergence_conditions="Residual RMS < 1e-4 mm or delta_q < 1e-5 mm within 50 iterations",
                failure_conditions="Singular normal matrix or RMS > 2.0 mm (inconsistent lengths)",
                computational_complexity="O(iter * (4 * 2^2 + 2^3)) = O(iter) where iter <= 15",
                execution_frequency="30 Hz state estimation cycle",
                subsystem_integration="Provides pose feedback to supervisor and digital twin telemetry",
                unit_tests="tests/unit/test_cdpr_kinematics.py::test_forward_kinematics_roundtrip",
                independent_validation="Round-trip synthetic test: IK -> add Gaussian noise -> FK recovery"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-JAC-001",
                name="Analytical Cable Jacobian & SVD Singularity Analysis",
                module="backend/app/kinematics/cdpr_kinematics.py",
                version="2.0.0",
                purpose="Map velocities between Cartesian and cable space and quantify kinematic conditioning",
                engineering_rationale="Analytical differentiation provides exact sensitivities; SVD prevents matrix inversion failure",
                inputs="Platform position (x, y)",
                outputs="Jacobian J (4x2), Unit vectors u_i (4x2), Condition number kappa(J), Pseudoinverse J^+",
                mathematical_formulation="J_i = (P_i - A_i)^T / L_i; J = U * Sigma * V^T; kappa = sigma_max / sigma_min",
                parameters="Threshold sigma_min >= 1e-4",
                parameter_units="Dimensionless unit directions, condition number kappa >= 1.0",
                numerical_method="Analytical differentiation + Singular Value Decomposition (SVD)",
                convergence_conditions="Analytical evaluation",
                failure_conditions="sigma_min < 1e-6 (kinematic singularity)",
                computational_complexity="O(1) for J, O(4*2^2) = O(16) for SVD",
                execution_frequency="30 Hz",
                subsystem_integration="Feeds tension solver, EKF measurement update, and controller feedforward",
                unit_tests="tests/unit/test_cdpr_kinematics.py::test_jacobian_structure_and_conditioning",
                independent_validation="Central finite-difference gradient verification J_num = (L(x+h) - L(x-h))/(2h)"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-OPT-001",
                name="Constrained Quadratic Programming Dynamic Tension Allocation",
                module="backend/app/dynamics/tension_solver.py",
                version="2.0.0",
                purpose="Allocate feasible positive cable tensions satisfying force equilibrium and dynamic acceleration",
                engineering_rationale="Antagonistic 4-cable redundancy requires bounded optimization to avoid slack and motor overload",
                inputs="Pose (x, y), Inertial acceleration [ax, ay], External wrench w_ext, Gravity g",
                outputs="Optimal tensions T = [T1, T2, T3, T4]^T, Equilibrium residual (N), Active constraints",
                mathematical_formulation="min_T 0.5 * ||A(q)T - b||^2 + alpha * ||T - T_mid||^2 s.t. T_min <= T_i <= T_max",
                parameters="T_min = 2.0 N, T_max = 50.0 N, T_mid = 18.0 N, alpha = 1e-4",
                parameter_units="Newtons (N)",
                numerical_method="Bounded Variable Least Squares (BVLS) active set optimization",
                convergence_conditions="Karush-Kuhn-Tucker (KKT) stationarity within bounds",
                failure_conditions="Equilibrium residual > 0.20 N (pose outside wrench-feasible workspace)",
                computational_complexity="O(iter * n^3) for n=4 cables (typically <= 5 iterations)",
                execution_frequency="30 Hz simulation clock & trajectory pre-check",
                subsystem_integration="Couples kinematics to physical cable tension state and safety interlocks",
                unit_tests="tests/physics/test_tension_solver.py::test_tension_at_nominal_center",
                independent_validation="Static equilibrium balance check sum(T_i * u_i) + F_ext = 0"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-CAB-001",
                name="Unilateral Kelvin-Voigt Cable Elasticity & Multilayer Drum Dynamics",
                module="backend/app/cables/cable_system.py",
                version="2.0.0",
                purpose="Model Dyneema SK75 axial elongation, viscous damping, and non-linear drum payout",
                engineering_rationale="Cables only transmit positive tension (unilateral); drum layer shifts effective radius",
                inputs="Geometric commanded length L_geom, Cable tension T, Payout rate L_dot",
                outputs="Actual physical cable length L_act, Elastic stretch delta_L, Drum layer, Slack status",
                mathematical_formulation="T = max(0, k * delta + c * delta_dot); delta = (F * L) / (E * A); r_eff = r_0 + layer * d",
                parameters="E = 100 GPa, d = 1.0 mm, c = 0.05 N*s/mm, T_slack = 2.0 N",
                parameter_units="E: MPa, k: N/mm, c: N*s/mm, r_eff: mm",
                numerical_method="Constitutive unilateral mechanical simulation",
                convergence_conditions="Deterministic state update per timestep",
                failure_conditions="Tensile load T > 65.0 N (cable overload) or T < 2.0 N (slack sag)",
                computational_complexity="O(1) per cable",
                execution_frequency="30 Hz",
                subsystem_integration="Couples motor rotational position to platform kinematic attachment",
                unit_tests="tests/physics/test_cables_and_motors.py::test_dyneema_elastic_elongation",
                independent_validation="Hooke's law beam analysis comparison"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-MOT-001",
                name="Jerk-Limited 7-Phase S-Curve Trajectory Generation",
                module="backend/app/motion/s_curve_planner.py",
                version="2.0.0",
                purpose="Generate time-optimal, continuous jerk-bounded trajectories preventing cable vibration",
                engineering_rationale="Step acceleration profiles cause cable snap and motor stall; S-curves bound mechanical shock",
                inputs="Target displacement D (mm), v_max, a_max, j_max",
                outputs="Analytical trajectory s(t), v(t), a(t), j(t) across 7 distinct phases",
                mathematical_formulation="Phase 1-3: Accel ramp (jerk +J to -J); Phase 4: Const velocity; Phase 5-7: Decel ramp",
                parameters="v_max = 120 mm/s, a_max = 400 mm/s^2, j_max = 2000 mm/s^3",
                parameter_units="mm/s, mm/s^2, mm/s^3, seconds",
                numerical_method="Analytical phase boundary integration",
                convergence_conditions="Continuous C^2 path arriving with zero terminal velocity and acceleration",
                failure_conditions="Target coordinate outside printable boundary margin",
                computational_complexity="O(1) planning, O(1) sampling per step",
                execution_frequency="Trajectory planning phase",
                subsystem_integration="Feeds Cartesian setpoints to Cascaded CDPR Controller",
                unit_tests="tests/test_processor_cam.py",
                independent_validation="Derivative continuity check: d/dt(s) = v, d/dt(v) = a, d/dt(a) = j"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-PTH-001",
                name="Ramer-Douglas-Peucker Polyline Simplification",
                module="backend/app/motion/s_curve_planner.py",
                version="2.0.0",
                purpose="Reduce redundant vector path vertices while guaranteeing geometric fidelity within epsilon",
                engineering_rationale="Eliminates sub-millimeter collinear waypoints to avoid motor stuttering and controller buffer lag",
                inputs="Ordered polyline vertices [(x1, y1)..], physical tolerance epsilon_mm",
                outputs="Simplified polyline with minimal vertex count",
                mathematical_formulation="Perpendicular distance d = |v x (P1 - P)| / |v|; retain vertex if d > epsilon",
                parameters="epsilon_mm = 0.5 mm (0.0005 m)",
                parameter_units="mm",
                numerical_method="Recursive divide-and-conquer computational geometry",
                convergence_conditions="All discarded vertices strictly within epsilon distance of chord",
                failure_conditions="Empty or single-point input",
                computational_complexity="O(N log N) average, O(N^2) worst case",
                execution_frequency="Once per vector artwork import",
                subsystem_integration="Feeds trajectory planner from vector graphics pipeline",
                unit_tests="tests/test_processor_cam.py",
                independent_validation="Hausdorff distance check between original and simplified paths <= epsilon"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-PTH-002",
                name="Nearest-Neighbor + 2-Opt TSP Contour Path Ordering",
                module="backend/app/motion/s_curve_planner.py",
                version="2.0.0",
                purpose="Optimize non-printing air-travel order across independent vector contours",
                engineering_rationale="Minimizes print completion time and cable wear by solving traveling salesperson problem",
                inputs="List of M independent closed/open contours",
                outputs="Permuted list of contours minimizing rapid traverse path length",
                mathematical_formulation="min sum ||exit_i - entry_(i+1)||^2; 2-opt inversion if cost(new) < cost(current)",
                parameters="Maximum 2-opt search iterations = 50",
                parameter_units="mm total air-distance",
                numerical_method="Greedy Nearest-Neighbor initialization + 2-Opt pairwise edge swap",
                convergence_conditions="No 2-opt swap yields cost improvement delta > 1e-4",
                failure_conditions="No valid contours provided",
                computational_complexity="O(M^2) for NN, O(M^2) per 2-opt pass",
                execution_frequency="Once per multi-contour print job",
                subsystem_integration="Orders CAM paths before S-curve time parameterization",
                unit_tests="tests/test_processor_cam.py",
                independent_validation="Comparison against unordered random contour sequence"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-CTL-001",
                name="Cascaded Cartesian PID & Cable Velocity Feedforward Controller",
                module="backend/app/control/cascaded_controller.py",
                version="2.0.0",
                purpose="Regulate platform position and generate synchronized cable velocity feedforward rates",
                engineering_rationale="Cascading position feedback with kinematic feedforward eliminates tracking phase lag",
                inputs="Target pos/vel (q_tgt, v_tgt), actual pos q_act, timestep dt",
                outputs="Cartesian commanded velocity v_cmd, Cable rates L_dot_cmd, Tracking metrics",
                mathematical_formulation="v_cmd = v_ff + Kp*e + Ki*int(e) + Kd*(de/dt); L_dot_cmd = J_L(q) * v_cmd",
                parameters="Kp = 4.5 1/s, Ki = 0.8 1/s^2, Kd = 0.25, anti-windup = 50mm, v_max = 120 mm/s",
                parameter_units="Gains: SI units; Output: mm/s",
                numerical_method="Discrete-time PID with trapezoidal integral and anti-windup clamping",
                convergence_conditions="Position tracking error converges to steady state <= 0.05 mm",
                failure_conditions="Feedback saturation or divergence",
                computational_complexity="O(1) constant time",
                execution_frequency="30 Hz simulation clock",
                subsystem_integration="Drives winch motor step commands in orchestrator",
                unit_tests="tests/physics/test_cables_and_motors.py",
                independent_validation="Bode plot stability margin analysis & step response test"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-EST-001",
                name="Extended Kalman Filter with Joseph-Form Covariance",
                module="backend/app/sensors/extended_kalman_filter.py",
                version="2.0.0",
                purpose="Estimate Cartesian platform position and velocity from noisy cable encoder measurements",
                engineering_rationale="Fuses non-linear kinematic measurements; Joseph form guarantees positive semi-definite covariance",
                inputs="Measured cable lengths z = [L1..L4], timestep dt",
                outputs="Corrected state x = [x, y, vx, vy]^T, Covariance P, NIS statistic, Diagnostic validity",
                mathematical_formulation="x^- = F*x; P^- = F*P*F^T + Q; K = P^-*H^T*S^-1; P = (I - KH)*P^-(I - KH)^T + K*R*K^T",
                parameters="sigma_a = 150 mm/s^2, sigma_m = 0.5 mm, NIS threshold = 9.488 (chi^2_4)",
                parameter_units="mm, mm/s, mm^2",
                numerical_method="Nonlinear extended Kalman filtering with analytical Jacobian H = [J_L, 0]",
                convergence_conditions="Trace(P) bounded < 1000.0, NIS statistic < 9.488",
                failure_conditions="Outlier rejection on NIS test or matrix inversion failure",
                computational_complexity="O(n^3 + m^3) = O(4^3) = O(64) operations",
                execution_frequency="30 Hz",
                subsystem_integration="Feeds estimated pose to closed-loop controller and supervisor",
                unit_tests="tests/algorithmic/test_algorithmic_specification.py",
                independent_validation="Monte Carlo simulation with synthetic white noise vs true position"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-IMG-001",
                name="Serpentine Floyd-Steinberg Error Diffusion Dithering",
                module="backend/app/processing/dithering.py",
                version="2.0.0",
                purpose="Render continuous tone photographic artwork into discrete droplet deposition raster patterns",
                engineering_rationale="Serpentine traversal eliminates directional worming artifacts common to standard raster dithering",
                inputs="Grayscale or RGB image array (H, W), Pigment palette",
                outputs="Binary or quantized droplet actuation array",
                mathematical_formulation="Quantize pixel; diffuse error: right 7/16, bottom-left 3/16, bottom 5/16, bottom-right 1/16",
                parameters="Threshold = 128 (binary), or discrete RGB pigment palette",
                parameter_units="Color intensity [0..255]",
                numerical_method="Spatial error diffusion filter",
                convergence_conditions="Total image energy / luminance conservation",
                failure_conditions="Non-8-bit image or invalid channel count",
                computational_complexity="O(W * H) single-pass linear time",
                execution_frequency="Once per raster artwork CAM job",
                subsystem_integration="Feeds drop-on-demand nozzle firing schedule in progressive buffer",
                unit_tests="tests/test_processor_cam.py",
                independent_validation="Histogram average luminance preservation verification"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-IMG-002",
                name="Marching Squares 2D Vector Contour Extraction",
                module="backend/app/processing/contour_extractor.py",
                version="2.0.0",
                purpose="Extract smooth continuous vector contours from raster images for Module B (Marker) toolpaths",
                engineering_rationale="Isocontour tracing guarantees closed, geometrically clean boundaries without pixel staircase aliasing",
                inputs="Scalar image grid (H, W), Isovalue threshold",
                outputs="Ordered list of vector polylines in physical wall millimeters",
                mathematical_formulation="2x2 cell corner binary indexing [0..15], linear edge interpolation, topology chaining",
                parameters="Isovalue = 128.0, Scale = (target_w / W, target_h / H)",
                parameter_units="mm",
                numerical_method="Marching Squares lookup table + polyline chaining",
                convergence_conditions="Closed loop or boundary-terminated polylines",
                failure_conditions="Uniform flat image without isovalue crossing",
                computational_complexity="O(W * H + num_segments)",
                execution_frequency="Once during CAM vector processing",
                subsystem_integration="Feeds RDP simplification and 2-opt contour ordering",
                unit_tests="tests/test_processor_cam.py",
                independent_validation="Contour area integration vs thresholded pixel area"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-FLT-001",
                name="Residual & Cumulative Sum (CUSUM) Anomaly Detector",
                module="backend/app/safety/fault_detector.py",
                version="2.0.0",
                purpose="Detect mechanical cable anomalies, sensor drift, and tracking divergence before failure occurs",
                engineering_rationale="CUSUM accumulates persistent small deviations that rule-based static bounds miss",
                inputs="q_pred, q_obs, L_pred, L_meas, Tensions T",
                outputs="Anomaly status, CUSUM statistics, Fault category, Alarm message",
                mathematical_formulation="S_k = max(0, S_(k-1) + |r_k| - delta); Alarm if S_k >= h",
                parameters="delta_pos = 0.8 mm, h_pos = 8.0, delta_cable = 0.5 mm, h_cable = 6.0",
                parameter_units="mm, dimensionless CUSUM statistic",
                numerical_method="Sequential change-point detection (Page's CUSUM)",
                convergence_conditions="Real-time sequential evaluation per step",
                failure_conditions="Residual exceeds hard threshold (pos > 15mm, cable > 8mm)",
                computational_complexity="O(1) constant time",
                execution_frequency="30 Hz",
                subsystem_integration="Directly transitions Supervisory State Machine to FAULT or EMERGENCY_STOP",
                unit_tests="tests/safety/test_cable_safety.py",
                independent_validation="Injected bias step-change detection latency test"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-DEP-001",
                name="Progressive Spatial Deposition & Pigment Blending Model",
                module="backend/app/deposition/progressive_buffer.py",
                version="2.0.0",
                purpose="Simulate realistic physical pigment transfer, substrate absorption, and droplet accumulation",
                engineering_rationale="Section 16 mandates that final surface appearance emerges exclusively from deposition events",
                inputs="px_x, px_y, color_rgb, ee_pos_mm, radius_px, material absorption & spread",
                outputs="Accumulated 2400x1800 RGB surface array, Total droplets, Coverage ratio, Event log",
                mathematical_formulation="effective_radius = max(1, radius * spread); blended = patch * (1 - opacity) + ink * opacity",
                parameters="opacity = 0.98, spread = 1.05 (panel), 1.35 (plaster), resolution = 2400x1800",
                parameter_units="pixels, mm, RGB [0..255]",
                numerical_method="Subtractive pigment accumulation in float32 buffer",
                convergence_conditions="Bounded intensity [0..255] per pixel channel",
                failure_conditions="Coordinate out of canvas boundary",
                computational_complexity="O(pi * r^2) per droplet event",
                execution_frequency="Every continuous motion sub-step (~15-100 Hz)",
                subsystem_integration="Feeds 3D Digital Twin canvas texture and Quality Inspector",
                unit_tests="tests/printing/test_deposition_and_quality.py",
                independent_validation="Conservation of ink volume: sum(deposited_volume) == total_dispensed"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-QLT-001",
                name="Multi-Metric Quantitative Print Quality Inspector",
                module="backend/app/quality/quality_inspector.py",
                version="2.0.0",
                purpose="Evaluate finished print fidelity against reference raster across geometry and photometry",
                engineering_rationale="Section 16.5 forbids single fabricated scores; requires comprehensive multi-domain metrics",
                inputs="Actual printed canvas RGB, Target reference raster RGB",
                outputs="MSE, RMSE, PSNR (dB), SSIM index, Delta-E color error, Edge sharpness ratio",
                mathematical_formulation="MSE = mean((A - B)^2); PSNR = 20*log10(255/sqrt(MSE)); DeltaE = ||Lab_A - Lab_B||",
                parameters="Local window size = 7x7 for SSIM, CIE76 DeltaE formula",
                parameter_units="dB (PSNR), DeltaE units, percentage [0..100%]",
                numerical_method="Full-reference image quality assessment",
                convergence_conditions="Deterministic array comparison",
                failure_conditions="Dimension mismatch between target and printed buffers",
                computational_complexity="O(W * H) across channels",
                execution_frequency="Upon print job completion or on-demand inspection",
                subsystem_integration="Generates formal CompletedJobReport and audit records",
                unit_tests="tests/printing/test_deposition_and_quality.py::test_quality_inspection_metrics",
                independent_validation="Identity test (target == printed => PSNR=inf, MSE=0, SSIM=1.0)"
            ),
            AlgorithmRecord(
                algorithm_id="ALG-CAL-001",
                name="Geometric Self-Calibration & Parameter Identifiability Analysis",
                module="backend/app/calibration/anchor_calibrator.py",
                version="2.0.0",
                purpose="Estimate unknown physical anchor positions and evaluate observation identifiability",
                engineering_rationale="Section 13 requires assessing Fisher Information rank before trusting calibration results",
                inputs="N calibration poses q_j, Measured cable lengths L_hat_ij, Initial anchor guesses",
                outputs="Refined anchor coordinates A1..A4, RMS error (mm), Fisher Information condition number, Identifiability status",
                mathematical_formulation="min_theta sum ||L_ij(theta) - L_hat_ij||^2; F = J_theta^T * J_theta; check cond(F)",
                parameters="Damping factor = 1e-2, Convergence tolerance RMS < 0.05 mm, Max iterations = 30",
                parameter_units="mm",
                numerical_method="Damped Gauss-Newton optimization with numerical Jacobian sensitivity",
                convergence_conditions="Residual RMS < 0.05 mm and delta_theta < 1e-4 mm",
                failure_conditions="Rank(F) < 8 (unidentifiable geometry) or divergence",
                computational_complexity="O(iter * (8 * N + 8^3))",
                execution_frequency="Commissioning & recalibration procedures",
                subsystem_integration="Updates kinematics AnchorPoint registry",
                unit_tests="tests/algorithmic/test_algorithmic_specification.py",
                independent_validation="Cross-validation against separate independent holdout poses"
            )
        ]

        for r in records:
            self._registry[r.algorithm_id] = r


# Global Singleton Registry Instance
GLOBAL_ALGORITHM_REGISTRY = AlgorithmRegistry()

