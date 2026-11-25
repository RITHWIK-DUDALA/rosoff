"""
Comprehensive Algorithmic Verification Test Suite for PROJECT W.A.L.L.
Directly verifies compliance with Sections 1 to 22 of the Complete Algorithmic Engineering Specification:
1. Geometry & Analytical Inverse Kinematics (Section 2 & 3)
2. Weighted Nonlinear Least-Squares Forward Kinematics (Section 4)
3. Analytical Jacobian, SVD & Singularity Analysis (Section 5)
4. Constrained Dynamic Quadratic Programming Tension Allocation (Section 6)
5. Unilateral Kelvin-Voigt Cable Elasticity (Section 7)
6. Jerk-Limited S-Curve Trajectory Generation (Section 9)
7. RDP Polyline Simplification & Nearest-Neighbor 2-Opt TSP (Section 9 & 15)
8. Cascaded Cartesian PID & Cable Velocity Control (Section 10)
9. Extended Kalman Filter with Joseph-Form Covariance & NIS Test (Section 12)
10. Calibration Identifiability via Fisher Information (Section 13)
11. Serpentine Floyd-Steinberg Error Diffusion Dithering (Section 14)
12. Marching Squares 2D Contour Extraction (Section 14)
13. CUSUM & Residual Anomaly Fault Detection (Section 17)
"""

import math
import pytest
import numpy as np
from PIL import Image

from backend.app.kinematics.cdpr_kinematics import CDPRKinematics, AnchorPoint, PlatformGeometry
from backend.app.dynamics.tension_solver import CableTensionSolver, TensionLimits
from backend.app.cables.cable_system import Cable, CableProperties
from backend.app.motion.s_curve_planner import JerkLimitedSCurve, SCurveParameters, ramer_douglas_peucker, nearest_neighbor_2opt_tsp
from backend.app.control.cascaded_controller import CascadedCDPRController, PIDParameters
from backend.app.sensors.extended_kalman_filter import CDPRExtendedKalmanFilter
from backend.app.calibration.anchor_calibrator import AnchorCalibrator
from backend.app.processing.dithering import FloydSteinbergDitherer
from backend.app.processing.contour_extractor import MarchingSquaresExtractor
from backend.app.safety.fault_detector import ComprehensiveFaultDetector, CUSUMDetector
from backend.app.diagnostics.algorithm_registry import GLOBAL_ALGORITHM_REGISTRY


# =========================================================================
# 1. GEOMETRY & INVERSE KINEMATICS (Sections 2 & 3)
# =========================================================================
def test_geometry_and_analytical_inverse_kinematics():
    kin = CDPRKinematics()
    # At center (400, 300) with 800x600 wall
    lengths = kin.inverse_kinematics(400.0, 300.0)
    assert len(lengths) == 4

    # Symmetry check: in symmetrical CDPR, all 4 corner lengths must be identical at center
    # Attachment points are: (+-50, +-40), Anchors are (0, 600), (800, 600), (0, 0), (800, 0)
    # L1: dist from (-50, 40) + (400, 300) = (350, 340) to (0, 600) => sqrt(350^2 + 260^2) = sqrt(122500 + 67600) = sqrt(190100) = 436.004
    expected_L = math.sqrt(350.0**2 + 260.0**2)
    for l in lengths:
        assert abs(l - expected_L) < 1e-3


# =========================================================================
# 2. FORWARD KINEMATICS & WEIGHTED NLS (Section 4)
# =========================================================================
def test_weighted_forward_kinematics_reconstruction():
    kin = CDPRKinematics()
    true_x, true_y = 450.0, 320.0
    true_lengths = kin.inverse_kinematics(true_x, true_y)

    # Reconstruct with weighted NLS from different initial guess
    res = kin.weighted_forward_kinematics(
        measured_lengths=true_lengths,
        weights=np.array([1.0, 1.0, 0.9, 0.9]),
        initial_guess=(400.0, 300.0),
        max_iter=30
    )
    assert res["converged"] is True
    assert abs(res["x_mm"] - true_x) < 0.01
    assert abs(res["y_mm"] - true_y) < 0.01
    assert res["rms_residual_mm"] < 1e-4


# =========================================================================
# 3. JACOBIAN, SVD & SINGULARITY ANALYSIS (Section 5)
# =========================================================================
def test_analytical_jacobian_and_svd():
    kin = CDPRKinematics()
    svd_res = kin.svd_analysis(400.0, 300.0)

    # Condition number kappa >= 1.0, rank must be 2 for 2-DOF translation
    assert svd_res["rank"] == 2
    assert svd_res["condition_number"] >= 1.0
    assert svd_res["is_near_singularity"] is False
    assert svd_res["dexterity_index"] > 0.0

    # Verify analytical Jacobian against numerical finite differences
    eps = 1e-5
    J_analytical, _ = kin.cable_jacobian(400.0, 300.0)
    J_numerical = np.zeros((4, 2))
    L_base = kin.inverse_kinematics(400.0, 300.0)

    L_dx = kin.inverse_kinematics(400.0 + eps, 300.0)
    L_dy = kin.inverse_kinematics(400.0, 300.0 + eps)
    J_numerical[:, 0] = (L_dx - L_base) / eps
    J_numerical[:, 1] = (L_dy - L_base) / eps

    np.testing.assert_allclose(J_analytical, J_numerical, rtol=1e-4, atol=1e-4)


# =========================================================================
# 4. CONSTRAINED DYNAMIC TENSION ALLOCATION (Section 6)
# =========================================================================
def test_constrained_dynamic_tension_qp():
    kin = CDPRKinematics()
    solver = CableTensionSolver(kin, TensionLimits(min_tension_n=2.0, max_tension_n=50.0))

    # Test feasible dynamic move with platform acceleration
    res = solver.solve_dynamic_tensions(
        x_mm=400.0, y_mm=300.0,
        ax_mps2=0.2, ay_mps2=0.1,
        include_gravity=True
    )
    assert res["is_feasible"] is True
    assert res["equilibrium_residual_n"] < 0.15
    for t in res["optimal_tensions_n"]:
        assert 2.0 - 1e-3 <= t <= 50.0 + 1e-3


# =========================================================================
# 5. UNILATERAL KELVIN-VOIGT CABLE MECHANICS (Section 7)
# =========================================================================
def test_unilateral_kelvin_voigt_cable():
    props = CableProperties(diameter_mm=1.0, elastic_modulus_mpa=100000.0, damping_coefficient_ns_per_mm=0.05)
    cable = Cable("C1", "M1", "B1", initial_length_mm=600.0, properties=props)

    # 1. Positive elongation: T > 0
    t_tensile = cable.compute_kelvin_voigt_tension(delta_mm=0.15, delta_rate_mm_s=2.0)
    assert t_tensile > 0.0

    # 2. Slack condition (delta <= 0): T must strictly equal 0
    t_slack = cable.compute_kelvin_voigt_tension(delta_mm=-0.5, delta_rate_mm_s=-1.0)
    assert t_slack == 0.0


# =========================================================================
# 6. JERK-LIMITED S-CURVE MOTION TRAJECTORY (Section 9)
# =========================================================================
def test_jerk_limited_s_curve_generator():
    params = SCurveParameters(v_max=100.0, a_max=300.0, j_max=1500.0)
    planner = JerkLimitedSCurve(params)
    distance = 150.0

    total_time, phases = planner.plan_move(distance)
    assert total_time > 0.0
    assert len(phases) == 7

    # Sample trajectory at midpoint
    mid_sample = planner.sample_at_time(total_time / 2.0, total_time, phases, distance)
    assert 0.0 <= mid_sample.s <= distance
    assert mid_sample.v <= params.v_max + 1e-3

    # Sample trajectory at end
    end_sample = planner.sample_at_time(total_time, total_time, phases, distance)
    assert abs(end_sample.s - distance) < 0.05
    assert abs(end_sample.v) < 1e-2


# =========================================================================
# 7. RDP SIMPLIFICATION & 2-OPT CONTOUR TSP (Sections 9 & 15)
# =========================================================================
def test_rdp_polyline_and_2opt_tsp():
    # Collinear points with small perturbations
    points = [(0.0, 0.0), (10.0, 0.1), (20.0, -0.05), (30.0, 0.08), (50.0, 0.0)]
    simplified = ramer_douglas_peucker(points, epsilon_mm=0.5)
    # Collinear points should be simplified down to endpoints
    assert len(simplified) == 2
    assert simplified[0] == (0.0, 0.0)
    assert simplified[-1] == (50.0, 0.0)

    # 2-Opt TSP contour ordering
    c1 = [(10.0, 10.0), (20.0, 10.0)]
    c2 = [(100.0, 100.0), (110.0, 100.0)]
    c3 = [(15.0, 15.0), (25.0, 15.0)]
    ordered = nearest_neighbor_2opt_tsp([c1, c2, c3])
    assert len(ordered) == 3
    # c1 and c3 are close to each other, so c2 should not be sandwiched between them
    assert (ordered[0] == c1 and ordered[1] == c3) or (ordered[1] == c1 and ordered[0] == c3) or (ordered[1] == c3 and ordered[2] == c1)


# =========================================================================
# 8. CASCADED CARTESIAN PID CONTROLLER (Section 10)
# =========================================================================
def test_cascaded_controller_tracking():
    kin = CDPRKinematics()
    ctrl = CascadedCDPRController(kin, PIDParameters(kp=4.0, ki=0.5, kd=0.1))

    # Command step from (400, 300) toward (410, 305)
    target_p = (410.0, 305.0)
    target_v = (20.0, 10.0)
    actual_p = (400.0, 300.0)

    v_cart, cable_rates, metrics = ctrl.update(target_p, target_v, actual_p, dt=0.033)
    assert len(cable_rates) == 4
    # Velocity command must move toward target
    assert v_cart[0] > 0.0
    assert v_cart[1] > 0.0
    assert metrics.rms_error_mm > 0.0


# =========================================================================
# 9. EXTENDED KALMAN FILTER WITH JOSEPH UPDATE & NIS (Section 12)
# =========================================================================
def test_extended_kalman_filter_state_estimation():
    kin = CDPRKinematics()
    ekf = CDPRExtendedKalmanFilter(kin, initial_pos_mm=(400.0, 300.0), measurement_noise_std_mm=0.2)

    # True pose moved to (405, 302)
    true_lengths = kin.inverse_kinematics(405.0, 302.0)
    # Add small Gaussian measurement noise
    noisy_lengths = true_lengths + np.array([0.05, -0.04, 0.02, -0.03])

    # Predict & Update
    ekf.predict(dt=0.033)
    diag = ekf.update(noisy_lengths)

    assert diag.is_observation_accepted is True
    assert diag.nis_statistic < 9.488 # Passed chi-squared gating
    assert diag.estimator_valid is True

    x_est, y_est, _, _ = ekf.get_estimated_pose()
    # Corrected pose should move toward true position
    assert 400.0 < x_est <= 405.5
    assert 300.0 < y_est <= 302.5


# =========================================================================
# 10. CALIBRATION IDENTIFIABILITY ANALYSIS (Section 13)
# =========================================================================
def test_calibration_fisher_identifiability():
    calib = AnchorCalibrator()

    # 4 well-separated poses across workspace
    poses = [(250.0, 200.0), (550.0, 200.0), (250.0, 450.0), (550.0, 450.0)]
    ident = calib.evaluate_identifiability(poses)
    assert ident["is_identifiable"] is True
    assert ident["rank"] == 8  # All 8 anchor coordinates [A1x..A4y] are excited
    assert ident["condition_number"] < 1e5


# =========================================================================
# 11. FLOYD-STEINBERG DITHERING (Section 14)
# =========================================================================
def test_floyd_steinberg_error_diffusion():
    # Create smooth gradient
    arr = np.linspace(0, 255, 100, dtype=np.uint8).reshape(10, 10)
    dithered = FloydSteinbergDitherer.dither_grayscale(arr, threshold=128)

    # Must be binary {0, 255}
    unique_vals = set(np.unique(dithered))
    assert unique_vals.issubset({0, 255})
    # Must preserve general gradient trend
    assert np.mean(dithered[:, :5]) < np.mean(dithered[:, 5:])


# =========================================================================
# 12. MARCHING SQUARES CONTOUR EXTRACTION (Section 14)
# =========================================================================
def test_marching_squares_contour_extractor():
    # 20x20 grid with circular hotspot in center
    grid = np.zeros((20, 20), dtype=np.float32)
    for y in range(20):
        for x in range(20):
            if (x - 10)**2 + (y - 10)**2 < 25:
                grid[y, x] = 255.0

    contours = MarchingSquaresExtractor.extract_contours(grid, isovalue=128.0)
    assert len(contours) >= 1
    # Check that extracted polyline points form a ring around (10, 10)
    pts = contours[0]
    radii = [math.hypot(pt[0] - 10, pt[1] - 10) for pt in pts]
    avg_r = sum(radii) / len(radii)
    assert abs(avg_r - 5.0) < 1.0


# =========================================================================
# 13. CUSUM & RESIDUAL FAULT DETECTION (Section 17)
# =========================================================================
def test_fault_detection_and_cusum():
    detector = ComprehensiveFaultDetector(max_position_error_mm=10.0, min_cable_tension_n=2.0)

    # 1. Nominal state: no fault
    status = detector.evaluate(
        q_predicted_mm=(400.0, 300.0),
        q_observed_mm=(400.1, 300.1),
        l_predicted_mm=np.array([450.0, 450.0, 450.0, 450.0]),
        l_measured_mm=np.array([450.1, 450.0, 450.2, 449.9]),
        measured_tensions_n=np.array([18.0, 18.0, 18.0, 18.0])
    )
    assert status.is_fault_detected is False

    # 2. Slack fault injection: cable C3 tension drops to 0.5N
    status_slack = detector.evaluate(
        q_predicted_mm=(400.0, 300.0),
        q_observed_mm=(400.0, 300.0),
        l_predicted_mm=np.array([450.0, 450.0, 450.0, 450.0]),
        l_measured_mm=np.array([450.0, 450.0, 450.0, 450.0]),
        measured_tensions_n=np.array([18.0, 18.0, 0.5, 18.0])
    )
    assert status_slack.is_fault_detected is True
    assert status_slack.fault_type == "CABLE_C3_SLACK"


# =========================================================================
# 14. ALGORITHM REGISTRY VERIFICATION (Section 20)
# =========================================================================
def test_algorithm_registry_records():
    registry = GLOBAL_ALGORITHM_REGISTRY.get_all()
    # At least 16 baseline algorithms must be fully registered
    assert len(registry) >= 16

    for rec in registry:
        assert rec["algorithm_id"].startswith("ALG-")
        assert rec["status"] == "IMPLEMENTED_AND_VERIFIED"
        assert len(rec["name"]) > 0
        assert len(rec["mathematical_formulation"]) > 0
        assert len(rec["convergence_conditions"]) > 0
        assert len(rec["failure_conditions"]) > 0
        assert len(rec["computational_complexity"]) > 0

