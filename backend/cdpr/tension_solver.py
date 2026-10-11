"""
Static force allocation and cable tension feasibility solver for 4-cable planar CDPR.

Mathematical formulation:
Let J_L = dL/dq be the 4x2 cable-length Jacobian.
By principle of virtual work, the cable force acting on the platform in XY plane is:
  F_cable = - J_L^T * T
where T = [T_1, T_2, T_3, T_4]^T is the vector of cable tensions.

For static equilibrium under external planar force F_ext:
  - J_L^T * T + F_ext = 0  =>  J_L^T * T = F_ext

Subject to unilateral tension constraints and actuator limits:
  T_min <= T_i <= T_max  for i = 1..4
where T_min >= 0, and T_max = min(cable_max, (tau_max * efficiency) / drum_radius).

Tension allocation solver:
Since the system is redundantly actuated (4 cables for 2 translational DOF), there exists an internal tension subspace.
We solve the constrained optimization problem:
  minimize: (1/2) * || T - T_ref ||^2
  subject to:
    J_L^T * T = F_ext
    T_min <= T_i <= T_max
Using scipy.optimize.lsq_linear or active-set quadratic programming.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from scipy.optimize import lsq_linear
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.config import RobotConfig


@dataclass
class TensionSolverResult:
    is_feasible: bool
    status_code: str          # "FEASIBLE", "INFEASIBLE_TENSION", "SINGULAR_CONFIGURATION", "RESIDUAL_ERROR"
    tensions: np.ndarray      # (4,) tensions in Newtons
    residual_force: np.ndarray # (2,) equilibrium residual: J_L^T * T - F_ext
    residual_norm: float      # ||residual_force|| in N
    slack_cables: np.ndarray  # boolean mask of cables at T_min or slack
    message: str


class TensionSolver:
    def __init__(self, kinematics: Kinematics):
        self.kin = kinematics
        self.config = kinematics.config
        self.t_min = self.config.cables.min_tension_N
        # Cap t_max by actuator torque capability:
        # tau = T * r / eff  =>  T_motor_cap = (tau_max * eff) / r
        t_motor_cap = self.config.actuators.max_cable_force_from_motor_N
        self.t_max = min(self.config.cables.max_tension_N, t_motor_cap)
        self.residual_tol = self.config.simulation.solver_tolerances.equilibrium_residual_tol

    def solve(
        self,
        q: np.ndarray,
        F_ext: Optional[np.ndarray] = None,
        T_ref: Optional[np.ndarray] = None
    ) -> TensionSolverResult:
        """
        Solves static tension allocation at platform position q for external planar force F_ext.
        q: [x, y] in meters
        F_ext: [Fx, Fy] in Newtons (default [0, 0])
        T_ref: preferred tension bias (default mid-point between T_min and 20N)
        """
        q = np.asarray(q, dtype=np.float64).reshape(2)
        if F_ext is None:
            F_ext = np.zeros(2, dtype=np.float64)
        else:
            F_ext = np.asarray(F_ext, dtype=np.float64).reshape(2)

        try:
            J_L = self.kin.jacobian(q)  # (4, 2)
        except Exception as e:
            return TensionSolverResult(
                is_feasible=False,
                status_code="SINGULAR_CONFIGURATION",
                tensions=np.zeros(4),
                residual_force=F_ext,
                residual_norm=float(np.linalg.norm(F_ext)),
                slack_cables=np.ones(4, dtype=bool),
                message=f"Singular geometry at position {q}: {e}"
            )

        A_eq = J_L.T  # (2, 4)
        b_eq = F_ext  # (2,)

        # Nominal reference tension
        if T_ref is None:
            t_nom = max(self.t_min * 2.0, min(15.0, (self.t_min + self.t_max) / 2.0))
            T_ref = np.full(4, t_nom, dtype=np.float64)
        else:
            T_ref = np.asarray(T_ref, dtype=np.float64).reshape(4)

        # Objective: minimize || A_aug * T - b_aug ||^2
        # where A_aug = [ lambda_eq * A_eq ; I_4 ]
        #       b_aug = [ lambda_eq * b_eq ; T_ref ]
        # with T in [T_min, T_max]^4.
        lambda_eq = 1000.0  # Strong penalty weight for equilibrium condition
        A_aug = np.vstack([lambda_eq * A_eq, np.eye(4)])
        b_aug = np.concatenate([lambda_eq * b_eq, T_ref])

        bounds = (self.t_min, self.t_max)

        res = lsq_linear(A_aug, b_aug, bounds=bounds, method="bvls", tol=1e-8, max_iter=200)

        t_opt = res.x
        residual = A_eq @ t_opt - b_eq  # J_L^T * T - F_ext
        res_norm = float(np.linalg.norm(residual))

        slack = (t_opt <= self.t_min + 1e-4)

        if res_norm <= self.residual_tol and res.success:
            return TensionSolverResult(
                is_feasible=True,
                status_code="FEASIBLE",
                tensions=t_opt,
                residual_force=residual,
                residual_norm=res_norm,
                slack_cables=slack,
                message=f"Equilibrium feasible (residual {res_norm:.4e} N)"
            )
        else:
            return TensionSolverResult(
                is_feasible=False,
                status_code="INFEASIBLE_TENSION",
                tensions=t_opt,
                residual_force=residual,
                residual_norm=res_norm,
                slack_cables=slack,
                message=(
                    f"Infeasible static wrench: Equilibrium residual {res_norm:.4f} N "
                    f"exceeds tolerance {self.residual_tol:.4f} N within tension bounds [{self.t_min}, {self.t_max}] N"
                )
            )
