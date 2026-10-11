"""
Platform dynamics and rigid-cable hybrid constraint simulation.

Physical model:
- Horizontal operating plane: gravity acts along -Z and is supported by the guide rods and planar bed.
- Anti-rotation guide eliminates pitch, roll, and yaw degrees of freedom (rotation around Z = 0).
- Independent generalized coordinates are the 2 planar translations q = [x, y]^T.
- Planar equations of motion:
    M * q_ddot = F_cable + F_external + F_friction
  where M = m * I_2x2 (with m = 0.5 kg).
  F_cable = - J_L^T * T
- Cables are modeled as rigid, massless, unilateral tension-only members.
  Because cables are rigid, when cables are taut and actuators are in position-control or velocity-feedforward mode,
  the actual platform position tracks the kinematically commanded trajectory, with dynamics providing
  the required cable forces T:
    J_L^T * T = F_ext + F_fric - M * q_ddot
  This required dynamic wrench F_req = M * q_ddot - F_ext is allocated to tensions T by the TensionSolver.
- If required dynamic tensions violate T_min or T_max, tension saturation occurs.
- Evaluates holonomic constraint residuals:
    residual_i = L_i(q) - (L_0_i + r * theta_i)
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from backend.cdpr.config import RobotConfig
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver


@dataclass
class DynamicsState:
    q: np.ndarray             # [x, y] in meters
    q_dot: np.ndarray         # [vx, vy] in m/s
    q_ddot: np.ndarray        # [ax, ay] in m/s^2
    cable_tensions: np.ndarray # (4,) tensions in N
    dynamic_wrench: np.ndarray # (2,) required force F_req = M * q_ddot - F_ext in N
    constraint_residuals: np.ndarray # (4,) difference between cable length and winch spool state
    is_feasible: bool
    status_code: str


class PlatformDynamics:
    def __init__(self, kinematics: Kinematics, tension_solver: TensionSolver):
        self.kin = kinematics
        self.tension_solver = tension_solver
        self.config = kinematics.config
        self.m = self.config.platform.mass_kg
        self.M = self.m * np.eye(2)
        self.dt = self.config.simulation.timestep_s
        self.mu_fric = 0.05 # Dry friction coefficient
        self.g = 9.81

    def compute_required_wrench(
        self,
        q_dot: np.ndarray,
        q_ddot: np.ndarray,
        F_ext: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Calculates the required planar force F_req that cables must exert on the platform:
          F_req = M * q_ddot - F_ext + F_friction
        For horizontal plane, normal load = m * g.
        Friction opposes motion direction: F_friction = mu * m * g * sgn(q_dot)
        """
        if F_ext is None:
            F_ext = np.zeros(2, dtype=np.float64)
        else:
            F_ext = np.asarray(F_ext, dtype=np.float64).reshape(2)

        q_dot = np.asarray(q_dot, dtype=np.float64).reshape(2)
        q_ddot = np.asarray(q_ddot, dtype=np.float64).reshape(2)

        v_norm = float(np.linalg.norm(q_dot))
        if v_norm > 1e-4:
            fric_dir = q_dot / v_norm
            F_fric = self.mu_fric * self.m * self.g * fric_dir
        else:
            F_fric = np.zeros(2, dtype=np.float64)

        # Newton's second law: F_cable + F_ext - F_fric = M * q_ddot
        # => F_cable = M * q_ddot - F_ext + F_fric
        # But F_cable = - J_L^T * T
        # So: - J_L^T * T = M * q_ddot - F_ext + F_fric
        # => J_L^T * T = - (M * q_ddot - F_ext + F_fric)
        F_req_against_cables = - (self.M @ q_ddot - F_ext + F_fric)
        return F_req_against_cables

    def step(
        self,
        q_target: np.ndarray,
        q_dot_target: np.ndarray,
        q_ddot_target: np.ndarray,
        current_drum_spool_lengths: np.ndarray,
        F_ext: Optional[np.ndarray] = None
    ) -> DynamicsState:
        """
        Advances the hybrid dynamics model for one fixed timestep.
        """
        q = np.asarray(q_target, dtype=np.float64).reshape(2)
        q_dot = np.asarray(q_dot_target, dtype=np.float64).reshape(2)
        q_ddot = np.asarray(q_ddot_target, dtype=np.float64).reshape(2)

        # Calculate required wrench that cable tensions must supply
        F_demand = self.compute_required_wrench(q_dot, q_ddot, F_ext)

        # Solve tension allocation for this dynamic wrench: J_L^T * T = F_demand
        tension_res = self.tension_solver.solve(q, F_ext=F_demand)

        # Holonomic cable constraint check:
        # Physical cable length L_i(q) vs spool length
        geom_lengths = self.kin.geom.cable_lengths(q)
        residuals = geom_lengths - current_drum_spool_lengths

        return DynamicsState(
            q=q,
            q_dot=q_dot,
            q_ddot=q_ddot,
            cable_tensions=tension_res.tensions,
            dynamic_wrench=F_demand,
            constraint_residuals=residuals,
            is_feasible=tension_res.is_feasible,
            status_code=tension_res.status_code
        )
