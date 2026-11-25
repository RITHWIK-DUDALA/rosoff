"""
Planar 4-Cable Driven Parallel Robot (CDPR) Kinematics Module for PROJECT W.A.L.L.
Implements analytical inverse kinematics, analytical cable Jacobian,
Levenberg-Marquardt forward kinematics pose estimation, and kinematic conditioning
as specified in Part 8 of the Specification.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import numpy as np


@dataclass
class AnchorPoint:
    id: str
    x: float  # mm
    y: float  # mm

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y], dtype=np.float64)


@dataclass
class PlatformGeometry:
    width_mm: float = 100.0
    height_mm: float = 80.0
    thickness_mm: float = 6.0
    mass_kg: float = 0.50

    @property
    def local_attachments(self) -> List[np.ndarray]:
        """
        Four attachment points relative to platform center:
        b1: upper-left (-w/2, +h/2)
        b2: upper-right (+w/2, +h/2)
        b3: lower-left (-w/2, -h/2)
        b4: lower-right (+w/2, -h/2)
        """
        hw = self.width_mm / 2.0
        hh = self.height_mm / 2.0
        return [
            np.array([-hw, +hh], dtype=np.float64),  # B1
            np.array([+hw, +hh], dtype=np.float64),  # B2
            np.array([-hw, -hh], dtype=np.float64),  # B3
            np.array([+hw, -hh], dtype=np.float64),  # B4
        ]


class CDPRKinematics:
    def __init__(
        self,
        anchors: Optional[Any] = None,
        platform: Optional[PlatformGeometry] = None
    ):
        if isinstance(anchors, dict):
            self.anchors = list(anchors.values())
        elif anchors is not None:
            self.anchors = list(anchors)
        else:
            self.anchors = [
                AnchorPoint("A1", 0.0, 600.0),    # Upper-Left
                AnchorPoint("A2", 800.0, 600.0),  # Upper-Right
                AnchorPoint("A3", 0.0, 0.0),      # Lower-Left
                AnchorPoint("A4", 800.0, 0.0),    # Lower-Right
            ]
        self.platform = platform or PlatformGeometry()

    def get_global_attachment_points(self, x: float, y: float) -> List[np.ndarray]:
        """Calculates global coordinates P_i = (x, y) + b_i for all 4 cable attachments"""
        pos = np.array([x, y], dtype=np.float64)
        return [pos + b_i for b_i in self.platform.local_attachments]

    def inverse_kinematics(self, x: float, y: float) -> np.ndarray:
        """
        Analytical Inverse Kinematics (Section 8.3):
        L_i = sqrt((P_ix - A_ix)^2 + (P_iy - A_iy)^2)
        Returns array of 4 cable lengths in mm.
        """
        pts = self.get_global_attachment_points(x, y)
        lengths = []
        for i, P_i in enumerate(pts):
            A_i = self.anchors[i].as_array()
            diff = P_i - A_i
            dist = float(np.linalg.norm(diff))
            lengths.append(dist)
        return np.array(lengths, dtype=np.float64)

    def cable_jacobian(self, x: float, y: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Analytical Cable Jacobian Matrix J (4 x 2) (Section 8.5):
        dL_i / dx = (P_ix - A_ix) / L_i
        dL_i / dy = (P_iy - A_iy) / L_i
        Returns:
            J: (4, 2) Jacobian matrix
            unit_vectors: (4, 2) unit pull vectors pointing from P_i to A_i: u_i = (A_i - P_i) / L_i
        """
        pts = self.get_global_attachment_points(x, y)
        J = np.zeros((4, 2), dtype=np.float64)
        unit_vectors = np.zeros((4, 2), dtype=np.float64)

        for i, P_i in enumerate(pts):
            A_i = self.anchors[i].as_array()
            diff = P_i - A_i
            dist = float(np.linalg.norm(diff))
            if dist < 1e-6:
                dist = 1e-6
            # dL/dx, dL/dy
            J[i, 0] = diff[0] / dist
            J[i, 1] = diff[1] / dist

            # Unit pull vector pointing from P_i toward anchor A_i
            unit_vectors[i] = (A_i - P_i) / dist

        return J, unit_vectors

    def jacobian_matrix(self, x: float, y: float) -> np.ndarray:
        """Returns (4, 2) cable Jacobian matrix"""
        return self.cable_jacobian(x, y)[0]

    def forward_kinematics(
        self,
        measured_lengths: np.ndarray,
        initial_guess: Optional[Tuple[float, float]] = None,
        max_iter: int = 50,
        tol_mm: float = 1e-4
    ) -> Tuple[bool, float, float, float]:
        """
        Nonlinear Least-Squares Forward Kinematics (Section 8.4):
        Estimates end-effector (x, y) from 4 measured cable lengths.
        Returns: (success, x_mm, y_mm, residual_rms_mm)
        """
        if initial_guess is not None:
            pos = np.array([initial_guess[0], initial_guess[1]], dtype=np.float64)
        else:
            # Default to center of anchors
            avg_x = sum(a.x for a in self.anchors) / 4.0
            avg_y = sum(a.y for a in self.anchors) / 4.0
            pos = np.array([avg_x, avg_y], dtype=np.float64)

        damping = 1e-2

        for _ in range(max_iter):
            calc_lengths = self.inverse_kinematics(pos[0], pos[1])
            residual = calc_lengths - measured_lengths

            if np.linalg.norm(residual) < tol_mm:
                rms = float(np.sqrt(np.mean(residual ** 2)))
                return True, float(pos[0]), float(pos[1]), rms

            J, _ = self.cable_jacobian(pos[0], pos[1])
            # Levenberg-Marquardt step: (J^T J + lambda I) delta = - J^T r
            JT_J = J.T @ J
            diag = np.diag(np.diag(JT_J))
            delta = np.linalg.solve(JT_J + damping * diag, -J.T @ residual)

            pos += delta
            if np.linalg.norm(delta) < 1e-5:
                break

        final_residual = self.inverse_kinematics(pos[0], pos[1]) - measured_lengths
        rms = float(np.sqrt(np.mean(final_residual ** 2)))
        success = (rms < 2.0)  # Converged within 2mm
        return success, float(pos[0]), float(pos[1]), rms

    def svd_analysis(self, x: float, y: float) -> Dict[str, Any]:
        """
        Singular Value Decomposition (Section 5.2):
        J = U * Sigma * V^T
        Calculates condition number kappa(J) = sigma_max / sigma_min and rank.
        """
        J, _ = self.cable_jacobian(x, y)
        U, s, Vt = np.linalg.svd(J, full_matrices=False)
        sigma_max = float(s[0])
        sigma_min = float(s[-1]) if s[-1] > 1e-12 else 1e-12
        cond = float(sigma_max / sigma_min)
        rank = int(np.sum(s > 1e-6))
        is_singular = bool(sigma_min < 1e-4 or cond > 1e4)

        return {
            "jacobian": J,
            "U": U,
            "singular_values": s,
            "V_transpose": Vt,
            "condition_number": cond,
            "dexterity_index": float(1.0 / cond) if cond > 0 else 0.0,
            "rank": rank,
            "is_near_singularity": is_singular,
            "sigma_min": sigma_min,
            "sigma_max": sigma_max
        }

    def pseudoinverse(self, x: float, y: float) -> np.ndarray:
        """
        Moore-Penrose Pseudoinverse via SVD (Section 5.1):
        J^+ = V * Sigma^+ * U^T
        Returns (2, 4) pseudoinverse matrix relating cable length rates to platform velocities:
        q_dot = J^+ * L_dot
        """
        J, _ = self.cable_jacobian(x, y)
        U, s, Vt = np.linalg.svd(J, full_matrices=False)
        # Reciprocal of singular values with thresholding
        s_inv = np.array([1.0 / val if val > 1e-6 else 0.0 for val in s])
        # V * diag(s_inv) * U^T
        return (Vt.T * s_inv) @ U.T

    def weighted_forward_kinematics(
        self,
        measured_lengths: np.ndarray,
        weights: Optional[np.ndarray] = None,
        initial_guess: Optional[Tuple[float, float]] = None,
        max_iter: int = 50,
        tol_step_mm: float = 1e-5,
        tol_residual_mm: float = 1e-4
    ) -> Dict[str, Any]:
        """
        Weighted Nonlinear Least-Squares Forward Kinematics (Section 4.1):
        min_q 0.5 * sum(w_i * (L_i(q) - L_hat_i)^2)
        Uses Levenberg-Marquardt with documented confidence weights w_i.
        Returns complete solver diagnostics and termination reason.
        """
        if weights is None:
            weights = np.ones(4, dtype=np.float64)
        else:
            weights = np.asarray(weights, dtype=np.float64)
        W = np.diag(weights)

        if initial_guess is not None:
            pos = np.array([initial_guess[0], initial_guess[1]], dtype=np.float64)
        else:
            avg_x = sum(a.x for a in self.anchors) / 4.0
            avg_y = sum(a.y for a in self.anchors) / 4.0
            pos = np.array([avg_x, avg_y], dtype=np.float64)

        damping = 1e-2
        termination_reason = "MAX_ITERATIONS_REACHED"
        converged = False
        iteration_count = 0

        for it in range(max_iter):
            iteration_count = it + 1
            calc_lengths = self.inverse_kinematics(pos[0], pos[1])
            residual = calc_lengths - measured_lengths

            weighted_res_norm = float(np.sqrt(np.mean(weights * (residual ** 2))))
            if weighted_res_norm < tol_residual_mm:
                termination_reason = "RESIDUAL_TOLERANCE_SATISFIED"
                converged = True
                break

            J, _ = self.cable_jacobian(pos[0], pos[1])
            # Weighted LM normal equations: (J^T W J + lambda diag(J^T W J)) delta = - J^T W r
            JTW = J.T @ W
            JTWJ = JTW @ J
            diag_damp = np.diag(np.diag(JTWJ)) + 1e-6 * np.eye(2)

            try:
                delta = np.linalg.solve(JTWJ + damping * diag_damp, -JTW @ residual)
            except np.linalg.LinAlgError:
                termination_reason = "SINGULAR_MATRIX_DIVERGENCE"
                break

            step_norm = float(np.linalg.norm(delta))
            pos += delta

            if step_norm < tol_step_mm:
                termination_reason = "STEP_SIZE_TOLERANCE_SATISFIED"
                converged = True
                break

        final_residual = self.inverse_kinematics(pos[0], pos[1]) - measured_lengths
        rms = float(np.sqrt(np.mean(weights * (final_residual ** 2))))

        return {
            "converged": bool(converged and rms < 2.0),
            "x_mm": float(pos[0]),
            "y_mm": float(pos[1]),
            "rms_residual_mm": round(rms, 4),
            "iterations": iteration_count,
            "termination_reason": termination_reason,
            "residual_vector_mm": final_residual
        }

    def kinematic_conditioning_index(self, x: float, y: float) -> float:
        """
        Condition number of Jacobian: measures distance from kinematic singularity.
        Returns normalized dexterity index in [0, 1] where 1.0 is isotropic.
        """
        J, _ = self.cable_jacobian(x, y)
        try:
            s = np.linalg.svd(J, compute_uv=False)
            if s[-1] < 1e-6:
                return 0.0
            cond = s[0] / s[-1]
            return float(1.0 / cond)
        except Exception:
            return 0.0
