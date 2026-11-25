"""
Anchor Geometry Auto-Calibration & Cable Homing Module for PROJECT W.A.L.L.
Implements kinematic self-calibration of anchor coordinates (A1..A4) and
cable zero-point homing via trilateration as specified in Section 7.1.
"""

from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np
from dataclasses import dataclass

from ..kinematics.cdpr_kinematics import AnchorPoint, PlatformGeometry


@dataclass
class CalibrationResult:
    is_converged: bool
    iterations: int
    rms_error_mm: float
    calibrated_anchors: Dict[str, AnchorPoint]
    nominal_discrepancy_mm: float


class AnchorCalibrator:
    def __init__(self, platform: Optional[PlatformGeometry] = None):
        self.platform = platform or PlatformGeometry()

    def calibrate_from_measurement_points(
        self,
        measured_poses: List[Tuple[float, float]],
        measured_cable_lengths: List[List[float]],
        initial_anchor_guesses: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> CalibrationResult:
        """
        Non-linear least squares optimization to refine anchor coordinates (A1..A4)
        from a set of N calibration poses where platform coordinates and cable lengths are recorded.
        """
        # Default 800 x 600 mm initial guesses
        anchors = initial_anchor_guesses or {
            "A1": (0.0, 600.0),
            "A2": (800.0, 600.0),
            "A3": (0.0, 0.0),
            "A4": (800.0, 0.0),
        }

        # Vector of parameters to optimize: [A1x, A1y, A2x, A2y, A3x, A3y, A4x, A4y]
        param_vector = np.array([
            anchors["A1"][0], anchors["A1"][1],
            anchors["A2"][0], anchors["A2"][1],
            anchors["A3"][0], anchors["A3"][1],
            anchors["A4"][0], anchors["A4"][1]
        ], dtype=np.float64)

        b_offsets = self.platform.local_attachments

        def residuals(p):
            res_list = []
            curr_anchors = [
                np.array([p[0], p[1]]),
                np.array([p[2], p[3]]),
                np.array([p[4], p[5]]),
                np.array([p[6], p[7]])
            ]
            for pose_idx, (px, py) in enumerate(measured_poses):
                center = np.array([px, py])
                for c_idx in range(4):
                    P_i = center + b_offsets[c_idx]
                    A_i = curr_anchors[c_idx]
                    expected_len = np.linalg.norm(P_i - A_i)
                    actual_len = measured_cable_lengths[pose_idx][c_idx]
                    res_list.append(expected_len - actual_len)
            return np.array(res_list, dtype=np.float64)

        # Gauss-Newton / Levenberg iteration
        curr_p = param_vector.copy()
        converged = False
        rms = 0.0

        for it in range(30):
            r = residuals(curr_p)
            rms = float(np.sqrt(np.mean(r ** 2)))
            if rms < 0.05:
                converged = True
                break

            # Numerical Jacobian
            eps = 1e-4
            J = np.zeros((len(r), 8))
            for col in range(8):
                p_plus = curr_p.copy()
                p_plus[col] += eps
                r_plus = residuals(p_plus)
                J[:, col] = (r_plus - r) / eps

            # Damped update
            H = J.T @ J + 1e-2 * np.eye(8)
            g = J.T @ r
            delta = np.linalg.solve(H, -g)
            curr_p += delta

            if np.linalg.norm(delta) < 1e-4:
                converged = True
                break

        calibrated = {
            "A1": AnchorPoint("A1", float(curr_p[0]), float(curr_p[1])),
            "A2": AnchorPoint("A2", float(curr_p[2]), float(curr_p[3])),
            "A3": AnchorPoint("A3", float(curr_p[4]), float(curr_p[5])),
            "A4": AnchorPoint("A4", float(curr_p[6]), float(curr_p[7])),
        }

        discrepancy = float(np.linalg.norm(curr_p - param_vector))

        return CalibrationResult(
            is_converged=converged,
            iterations=it + 1,
            rms_error_mm=rms,
            calibrated_anchors=calibrated,
            nominal_discrepancy_mm=discrepancy
        )

    def evaluate_identifiability(self, measured_poses: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Evaluates parameter identifiability (Section 13.2):
        Calculates Fisher Information Matrix F = J^T * J, rank, and condition number.
        Guarantees that calibration dataset contains sufficient spatial excitation
        to uniquely identify all 8 anchor coordinates.
        """
        N = len(measured_poses)
        if N < 2:
            return {
                "is_identifiable": False,
                "reason": f"Insufficient poses ({N} < 2). Need at least 2 distinct non-collinear poses.",
                "rank": 0,
                "condition_number": float('inf'),
                "singular_values": []
            }

        nominal_anchors = [
            np.array([0.0, 600.0]),
            np.array([800.0, 600.0]),
            np.array([0.0, 0.0]),
            np.array([800.0, 0.0])
        ]
        b_offsets = self.platform.local_attachments

        # Build sensitivity Jacobian J_theta (N*4 rows, 8 cols)
        J = np.zeros((N * 4, 8), dtype=np.float64)

        for p_idx, (px, py) in enumerate(measured_poses):
            center = np.array([px, py])
            for c_idx in range(4):
                P_i = center + b_offsets[c_idx]
                A_i = nominal_anchors[c_idx]
                diff = P_i - A_i
                dist = np.linalg.norm(diff)
                row = p_idx * 4 + c_idx
                # d(L)/d(A_ix) = -(P_ix - A_ix) / L
                col = c_idx * 2
                if dist > 1e-6:
                    J[row, col] = -diff[0] / dist
                    J[row, col + 1] = -diff[1] / dist

        # Fisher Information Matrix F = J^T * J (8 x 8)
        F = J.T @ J
        s = np.linalg.svd(F, compute_uv=False)
        rank = int(np.sum(s > 1e-4))
        cond = float(s[0] / s[-1]) if s[-1] > 1e-9 else float('inf')
        is_identifiable = bool(rank == 8 and cond < 1e5)

        return {
            "is_identifiable": is_identifiable,
            "rank": rank,
            "condition_number": round(cond, 2),
            "singular_values": [float(round(val, 4)) for val in s],
            "reason": "Observations uniquely excite all 8 anchor parameters" if is_identifiable else "Ill-conditioned pose geometry"
        }

