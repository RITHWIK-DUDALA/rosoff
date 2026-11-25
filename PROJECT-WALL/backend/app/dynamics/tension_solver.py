"""
Cable Tension Allocation & Force Equilibrium Solver for PROJECT W.A.L.L.
Implements bounded quadratic programming (lsq_linear) for antagonistic static tension distribution,
positive tension verification (T_min <= T_i <= T_max), and workspace tension feasibility analysis
as specified in Part 5.4, 8.6, and 8.7 of the Specification.
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
import numpy as np
from scipy.optimize import lsq_linear

from ..kinematics.cdpr_kinematics import CDPRKinematics


@dataclass
class TensionLimits:
    min_tension_n: float = 2.0    # Minimum positive tension to prevent slack (N)
    max_tension_n: float = 50.0   # Maximum safe working load per cable (N)
    target_mid_tension_n: float = 18.0


@dataclass
class TensionDistributionResult:
    is_feasible: bool
    tensions_n: np.ndarray        # [T1, T2, T3, T4] in Newtons
    equilibrium_residual_n: float
    slack_cable_indices: list
    overloaded_cable_indices: list


class CableTensionSolver:
    def __init__(self, kinematics: CDPRKinematics, limits: Optional[TensionLimits] = None):
        self.kinematics = kinematics
        self.limits = limits or TensionLimits()

    def solve_static_tensions(
        self,
        x_mm: float,
        y_mm: float,
        f_ext_x: float = 0.0,
        f_ext_y: float = 0.0,
        include_gravity: bool = True
    ) -> TensionDistributionResult:
        """
        Solves static equilibrium:
        Structure Matrix A * T = - F_resultant
        where A = [u1, u2, u3, u4] (2 x 4)
        F_resultant = [F_ext_x, F_ext_y - m*g]
        Subject to: T_min <= T_i <= T_max
        """
        _, unit_vectors = self.kinematics.cable_jacobian(x_mm, y_mm)
        # Structure matrix A (2 x 4): rows are X and Y components of unit pull vectors
        A = unit_vectors.T  # (2, 4)

        # External forces + Gravity
        mass = self.kinematics.platform.mass_kg
        g = 9.81 if include_gravity else 0.0
        # W.A.L.L. is mounted on vertical/inclined wall: gravity pulls downward along -Y
        f_gravity_y = -mass * g

        # Required resultant force that cables must oppose:
        # A * T + F_ext + F_gravity = 0  =>  A * T = - (F_ext + F_gravity)
        b = np.array([
            -(f_ext_x),
            -(f_ext_y + f_gravity_y)
        ], dtype=np.float64)

        # Formulate quadratic programming problem:
        # Minimize || A*T - b ||^2 + alpha * || T - T_mid ||^2
        # subject to T_min <= T <= T_max
        alpha = 1e-4
        A_reg = np.vstack([A, np.sqrt(alpha) * np.eye(4)])
        b_reg = np.concatenate([b, np.sqrt(alpha) * np.full(4, self.limits.target_mid_tension_n)])

        res = lsq_linear(
            A_reg,
            b_reg,
            bounds=(self.limits.min_tension_n, self.limits.max_tension_n),
            method='bvls'
        )

        tensions = res.x
        residual = np.linalg.norm(A @ tensions - b)

        # Check feasibility
        is_feasible = (residual < 0.15) and np.all(tensions >= self.limits.min_tension_n - 1e-3) and np.all(tensions <= self.limits.max_tension_n + 1e-3)

        slack = [i for i, t in enumerate(tensions) if t <= self.limits.min_tension_n + 0.1]
        overloaded = [i for i, t in enumerate(tensions) if t >= self.limits.max_tension_n - 0.1]

        return TensionDistributionResult(
            is_feasible=bool(is_feasible),
            tensions_n=np.round(tensions, 2),
            equilibrium_residual_n=float(round(residual, 3)),
            slack_cable_indices=slack,
            overloaded_cable_indices=overloaded
        )

    def solve_dynamic_tensions(
        self,
        x_mm: float,
        y_mm: float,
        ax_mps2: float = 0.0,
        ay_mps2: float = 0.0,
        f_ext_x: float = 0.0,
        f_ext_y: float = 0.0,
        include_gravity: bool = True
    ) -> Dict[str, Any]:
        """
        Dynamic Tension Allocation (Section 6.3):
        Incorporates platform inertial forces (m * a) into dynamic force equilibrium:
        A(q) * T + F_ext + F_gravity - m * a = 0
        A(q) * T = - (F_ext + F_gravity - m * a)
        Subject to: T_min <= T_i <= T_max
        Returns full optimization diagnostics (Section 6.4).
        """
        _, unit_vectors = self.kinematics.cable_jacobian(x_mm, y_mm)
        A = unit_vectors.T  # (2, 4)

        mass = self.kinematics.platform.mass_kg
        g = 9.81 if include_gravity else 0.0
        f_gravity_y = -mass * g

        # Inertial forces: F_inertial = m * a
        f_inertial_x = mass * ax_mps2
        f_inertial_y = mass * ay_mps2

        # Net required force vector: b = - (F_ext + F_gravity - m*a)
        b = np.array([
            -(f_ext_x - f_inertial_x),
            -(f_ext_y + f_gravity_y - f_inertial_y)
        ], dtype=np.float64)

        alpha = 1e-4
        A_reg = np.vstack([A, np.sqrt(alpha) * np.eye(4)])
        b_reg = np.concatenate([b, np.sqrt(alpha) * np.full(4, self.limits.target_mid_tension_n)])

        res = lsq_linear(
            A_reg,
            b_reg,
            bounds=(self.limits.min_tension_n, self.limits.max_tension_n),
            method='bvls'
        )

        tensions = res.x
        residual = float(np.linalg.norm(A @ tensions - b))
        is_feasible = bool(
            (residual < 0.20) and
            np.all(tensions >= self.limits.min_tension_n - 1e-3) and
            np.all(tensions <= self.limits.max_tension_n + 1e-3)
        )

        # Active constraints
        active_lower = [int(i) for i, t in enumerate(tensions) if abs(t - self.limits.min_tension_n) < 1e-3]
        active_upper = [int(i) for i, t in enumerate(tensions) if abs(t - self.limits.max_tension_n) < 1e-3]

        return {
            "is_feasible": is_feasible,
            "optimal_tensions_n": np.round(tensions, 3),
            "objective_value": float(round(res.cost, 5)),
            "equilibrium_residual_n": round(residual, 4),
            "active_constraints": {"lower": active_lower, "upper": active_upper},
            "iterations": int(getattr(res, "nit", 0)),
            "solver_status": int(res.status),
            "failure_reason": None if is_feasible else f"Equilibrium residual {residual:.2f}N exceeds tolerance or tensions bounded"
        }

    def is_pose_feasible(self, x_mm: float, y_mm: float) -> bool:
        res = self.solve_static_tensions(x_mm, y_mm)
        return res.is_feasible
