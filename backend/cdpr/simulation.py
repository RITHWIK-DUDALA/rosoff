"""
Deterministic fixed-timestep simulation loop engine for CDPR.
Coordinates:
1. Command & trajectory reference updates
2. Analytical inverse kinematics & differential kinematics
3. Rigid-cable platform dynamics & tension allocation
4. Actuator speed & torque integration with saturation checks
5. Forward kinematics validation / pose recovery
6. Workspace, collision, tension, and fault monitoring
7. Telemetry compilation
"""
import time
import numpy as np
from typing import Optional, List, Dict, Any
from backend.cdpr.config import RobotConfig, load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver
from backend.cdpr.actuator import ActuatorArray
from backend.cdpr.collision import CollisionChecker
from backend.cdpr.dynamics import PlatformDynamics
from backend.cdpr.trajectory import TrajectoryPlanner
from backend.cdpr.controller import Controller
from backend.cdpr.state import TelemetryData


class CDPRSimulation:
    def __init__(self, config_path: str = "robot_config.yaml"):
        self.config = load_robot_config(config_path)
        self.geom = Geometry(self.config)
        self.kin = Kinematics(self.geom)
        self.tension_solver = TensionSolver(self.kin)
        self.actuators = ActuatorArray(self.config)
        self.collision = CollisionChecker(self.geom)
        self.dynamics = PlatformDynamics(self.kin, self.tension_solver)
        self.planner = TrajectoryPlanner(self.config, self.kin, self.tension_solver, self.collision)
        self.controller = Controller(self.config, self.planner)

        # Simulation time state
        self.dt = self.config.simulation.timestep_s
        self.sim_time = 0.0

        # Physical platform states: q = [x, y] in meters
        self.q = np.zeros(2, dtype=np.float64)
        self.q_dot = np.zeros(2, dtype=np.float64)
        self.q_ddot = np.zeros(2, dtype=np.float64)

        # Initialize spool lengths at home position
        init_lengths = self.geom.cable_lengths(self.q)
        self.actuators.reset(init_lengths)
        self.controller.set_position(self.q)

        # Latest telemetry snapshot
        self.latest_telemetry: Optional[TelemetryData] = None
        self._step_internal()

    def step(self):
        """Advances simulation by one fixed timestep dt."""
        self._step_internal()

    def _step_internal(self):
        # 1. Controller step: update reference trajectory state
        target_q, target_q_dot, target_q_ddot, progress_pct = self.controller.update_step()

        # In rigid-cable model, platform state tracks commanded reference when feasible
        if self.controller.mode == "MOVING":
            self.q = target_q.copy()
            self.q_dot = target_q_dot.copy()
            self.q_ddot = target_q_ddot.copy()
            self.controller.current_q = self.q.copy()
        elif self.controller.mode in ("IDLE", "PAUSED", "STOPPED", "ESTOP"):
            self.q_dot = np.zeros(2)
            self.q_ddot = np.zeros(2)

        # 2. Kinematics evaluation
        ik_res = self.kin.inverse_kinematics(self.q, q_dot=self.q_dot)
        cable_lengths = ik_res.lengths
        cable_rates = ik_res.lengths_dot if ik_res.lengths_dot is not None else np.zeros(4)
        J_L = ik_res.jacobian if ik_res.jacobian is not None else np.zeros((4, 2))
        cond_num = ik_res.condition_number

        # 3. Dynamic wrench and tension allocation
        dyn_state = self.dynamics.step(
            q_target=self.q,
            q_dot_target=self.q_dot,
            q_ddot_target=self.q_ddot,
            current_drum_spool_lengths=cable_lengths
        )

        # 4. Actuator integration and saturation checks
        servo_states = self.actuators.update(
            current_lengths=cable_lengths,
            cable_rates=cable_rates,
            cable_tensions=dyn_state.cable_tensions
        )

        motor_rpms = [s.motor_rpm for s in servo_states]
        motor_torques = [s.estimated_torque_Nm for s in servo_states]

        # 5. Collision & safety evaluation
        col_res = self.collision.check(self.q)

        # 6. Fault aggregation
        faults = list(self.controller.active_faults)
        if not col_res.is_safe:
            faults.append(col_res.violation_message)
        if not dyn_state.is_feasible:
            faults.append("INFEASIBLE_TENSION")
        for s in servo_states:
            if s.speed_saturated and "SPEED_LIMIT" not in faults:
                faults.append("SPEED_LIMIT")
            if s.torque_saturated and "TORQUE_LIMIT" not in faults:
                faults.append("TORQUE_LIMIT")

        # 7. Tracking error
        tracking_err_m = float(np.linalg.norm(self.q - target_q))

        # 8. Compile Telemetry
        self.latest_telemetry = TelemetryData(
            sim_time_s=self.sim_time,
            platform_x_mm=float(self.q[0] * 1000.0),
            platform_y_mm=float(self.q[1] * 1000.0),
            platform_vx_mm_s=float(self.q_dot[0] * 1000.0),
            platform_vy_mm_s=float(self.q_dot[1] * 1000.0),
            platform_ax_mm_s2=float(self.q_ddot[0] * 1000.0),
            platform_ay_mm_s2=float(self.q_ddot[1] * 1000.0),
            target_x_mm=float(target_q[0] * 1000.0),
            target_y_mm=float(target_q[1] * 1000.0),
            cable_lengths_mm=[float(l * 1000.0) for l in cable_lengths],
            cable_rates_mm_s=[float(r * 1000.0) for r in cable_rates],
            cable_tensions_N=[float(t) for t in dyn_state.cable_tensions],
            motor_speeds_rpm=motor_rpms,
            motor_torques_Nm=motor_torques,
            tracking_error_mm=float(tracking_err_m * 1000.0),
            controller_mode=self.controller.mode,
            workspace_safe=col_res.is_safe,
            collision_safe=col_res.is_safe,
            tension_feasible=dyn_state.is_feasible,
            solver_converged=ik_res.is_valid,
            constraint_residuals_mm=[float(c * 1000.0) for c in dyn_state.constraint_residuals],
            condition_number=float(cond_num),
            active_faults=faults,
            trajectory_progress_pct=progress_pct
        )

        self.sim_time += self.dt

    def reset(self):
        """Resets simulation to initial state."""
        self.sim_time = 0.0
        self.q = np.zeros(2, dtype=np.float64)
        self.q_dot = np.zeros(2, dtype=np.float64)
        self.q_ddot = np.zeros(2, dtype=np.float64)
        init_lengths = self.geom.cable_lengths(self.q)
        self.actuators.reset(init_lengths)
        self.controller.reset()
        self._step_internal()
