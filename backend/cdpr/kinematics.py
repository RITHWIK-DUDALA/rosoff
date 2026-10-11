"""
Kinematics engine for 4-cable planar robot.
Implements:
1. Analytical Inverse Kinematics (q -> L, L_dot)
2. Analytical Cable-Length Jacobian J_L = dL/dq
3. Differential Kinematics (L_dot = J_L * q_dot)
4. Robust Forward Kinematics (L_measured -> q via damped Gauss-Newton / Levenberg-Marquardt)
5. Singularity detection & condition number calculation.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from backend.cdpr.geometry import Geometry
from backend.cdpr.config import RobotConfig


@dataclass
class InverseKinematicsResult:
    q: np.ndarray             # [x, y] in meters
    lengths: np.ndarray       # (4,) lengths in meters
    lengths_dot: Optional[np.ndarray] = None # (4,) length rates in m/s
    jacobian: Optional[np.ndarray] = None    # (4, 2) Jacobian matrix
    condition_number: float = 1.0
    is_valid: bool = True
    message: str = "OK"


@dataclass
class ForwardKinematicsResult:
    q_estimated: np.ndarray   # [x, y] in meters
    converged: bool
    iterations: int
    residual_norm: float      # norm of ||L(q) - L_meas||
    residuals: np.ndarray     # (4,) residual errors in meters
    condition_number: float
    message: str = "Converged"


class Kinematics:
    def __init__(self, geometry: Geometry):
        self.geom = geometry
        self.config = geometry.config

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        """
        Computes the analytical 4x2 cable-length Jacobian J_L(q) = dL / dq.
        For cable i:
          L_i = sqrt((x + b_ix - A_ix)^2 + (y + b_iy - A_iy)^2)
          dL_i / dx = (x + b_ix - A_ix) / L_i
          dL_i / dy = (y + b_iy - A_iy) / L_i
        Notice that (x + b_ix - A_ix) = P_ix - A_ix = - (A_ix - P_ix).
        So J_L(q) row i = - u_i^T, where u_i is the unit vector pointing from attachment P_i to anchor A_i.
        Thus: L_dot = J_L(q) * q_dot.
        """
        q = np.asarray(q, dtype=np.float64).reshape(2)
        P = self.geom.platform_attachments_world(q)   # (4, 2)
        A = self.geom.anchors                         # (4, 2)
        diff = P - A                                  # (4, 2), diff_i = P_i - A_i
        L = np.linalg.norm(diff, axis=1, keepdims=True)
        if np.any(L <= 1e-6):
            raise ValueError(f"Singularity: cable length <= 1e-6 at q={q}")
        J_L = diff / L                                # (4, 2)
        return J_L

    def condition_number(self, J_L: np.ndarray) -> float:
        """Computes 2-norm condition number of Jacobian."""
        s = np.linalg.svd(J_L, compute_uv=False)
        if s[-1] < 1e-12:
            return float("inf")
        return float(s[0] / s[-1])

    def inverse_kinematics(self, q: np.ndarray, q_dot: Optional[np.ndarray] = None) -> InverseKinematicsResult:
        """
        Inverse kinematics: calculates 4 cable lengths and optional rates from platform state.
        """
        q = np.asarray(q, dtype=np.float64).reshape(2)
        # Check workspace limits
        ws = self.config.workspace
        if not (ws.x_min_m <= q[0] <= ws.x_max_m and ws.y_min_m <= q[1] <= ws.y_max_m):
            return InverseKinematicsResult(
                q=q,
                lengths=np.zeros(4),
                is_valid=False,
                message=f"Target [{q[0]:.3f}, {q[1]:.3f}] m outside workspace bounds [{ws.x_min_m}, {ws.x_max_m}], [{ws.y_min_m}, {ws.y_max_m}]"
            )

        try:
            lengths = self.geom.cable_lengths(q)
            J_L = self.jacobian(q)
            cond = self.condition_number(J_L)
            l_dot = None
            if q_dot is not None:
                q_dot = np.asarray(q_dot, dtype=np.float64).reshape(2)
                l_dot = J_L @ q_dot

            return InverseKinematicsResult(
                q=q,
                lengths=lengths,
                lengths_dot=l_dot,
                jacobian=J_L,
                condition_number=cond,
                is_valid=True,
                message="OK"
            )
        except Exception as e:
            return InverseKinematicsResult(
                q=q,
                lengths=np.zeros(4),
                is_valid=False,
                message=f"Kinematics error: {str(e)}"
            )

    def forward_kinematics(
        self,
        lengths_measured: np.ndarray,
        q_initial: Optional[np.ndarray] = None,
        weights: Optional[np.ndarray] = None,
        max_iterations: int = 50,
        tolerance: float = 1e-7,
        damping: float = 1e-4
    ) -> ForwardKinematicsResult:
        """
        Forward kinematics solver: Estimates platform position q = [x, y] from redundant measured cable lengths.
        Minimizes sum_i w_i * (L_i(q) - L_measured_i)^2 using damped Gauss-Newton / Levenberg-Marquardt.
        """
        L_meas = np.asarray(lengths_measured, dtype=np.float64).reshape(4)
        if np.any(L_meas <= 0.0):
            return ForwardKinematicsResult(
                q_estimated=np.zeros(2),
                converged=False,
                iterations=0,
                residual_norm=float("inf"),
                residuals=np.zeros(4),
                condition_number=float("inf"),
                message="Invalid negative or zero measured cable lengths"
            )

        if q_initial is None:
            q_k = np.zeros(2, dtype=np.float64)  # Center of workspace
        else:
            q_k = np.array(q_initial, dtype=np.float64).reshape(2)

        W = np.eye(4) if weights is None else np.diag(np.asarray(weights, dtype=np.float64).reshape(4))

        mu = damping
        converged = False
        final_iter = 0
        r_k = np.zeros(4)

        for it in range(max_iterations):
            final_iter = it + 1
            try:
                L_k = self.geom.cable_lengths(q_k)
                r_k = L_k - L_meas  # residual vector (4,)
                res_norm = float(np.linalg.norm(r_k))

                if res_norm < tolerance:
                    converged = True
                    break

                J_k = self.jacobian(q_k)  # (4, 2)
                # Levenberg-Marquardt normal equation:
                # (J^T W J + mu * I) delta_q = - J^T W r
                JT_W = J_k.T @ W
                H = JT_W @ J_k + mu * np.eye(2)
                g = - JT_W @ r_k

                delta_q = np.linalg.solve(H, g)

                # Test trial step
                q_trial = q_k + delta_q
                L_trial = self.geom.cable_lengths(q_trial)
                r_trial = L_trial - L_meas
                if np.linalg.norm(r_trial) < res_norm:
                    # Accept step and decrease damping
                    q_k = q_trial
                    mu = max(1e-7, mu * 0.5)
                    if np.linalg.norm(delta_q) < tolerance:
                        converged = True
                        r_k = r_trial
                        break
                else:
                    # Reject step and increase damping
                    mu = min(1e3, mu * 4.0)

            except Exception as ex:
                return ForwardKinematicsResult(
                    q_estimated=q_k,
                    converged=False,
                    iterations=it + 1,
                    residual_norm=float("inf"),
                    residuals=r_k,
                    condition_number=float("inf"),
                    message=f"Singularity or divergence during FK solver: {ex}"
                )

        try:
            J_final = self.jacobian(q_k)
            cond = self.condition_number(J_final)
        except Exception:
            cond = float("inf")

        final_res_norm = float(np.linalg.norm(r_k))
        # If residuals are very large even after iteration, lengths are geometrically incompatible
        if converged and final_res_norm > 0.05:  # > 50 mm residual
            return ForwardKinematicsResult(
                q_estimated=q_k,
                converged=False,
                iterations=final_iter,
                residual_norm=final_res_norm,
                residuals=r_k,
                condition_number=cond,
                message=f"Incompatible cable lengths: residual norm {final_res_norm*1000:.2f} mm exceeds tolerance"
            )

        return ForwardKinematicsResult(
            q_estimated=q_k,
            converged=converged,
            iterations=final_iter,
            residual_norm=final_res_norm,
            residuals=r_k,
            condition_number=cond,
            message="Converged" if converged else "Max iterations reached without convergence"
        )
