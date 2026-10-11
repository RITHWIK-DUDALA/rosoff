"""
State definitions, telemetry payloads, and command data structures for CDPR simulator.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np


@dataclass
class TelemetryData:
    sim_time_s: float
    platform_x_mm: float
    platform_y_mm: float
    platform_vx_mm_s: float
    platform_vy_mm_s: float
    platform_ax_mm_s2: float
    platform_ay_mm_s2: float
    target_x_mm: float
    target_y_mm: float
    cable_lengths_mm: List[float]
    cable_rates_mm_s: List[float]
    cable_tensions_N: List[float]
    motor_speeds_rpm: List[float]
    motor_torques_Nm: List[float]
    tracking_error_mm: float
    controller_mode: str      # "IDLE", "MOVING", "PAUSED", "STOPPED", "FAULT", "ESTOP"
    workspace_safe: bool
    collision_safe: bool
    tension_feasible: bool
    solver_converged: bool
    constraint_residuals_mm: List[float]
    condition_number: float
    active_faults: List[str]
    trajectory_progress_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sim_time_s": round(self.sim_time_s, 3),
            "platform_pos": [round(self.platform_x_mm, 2), round(self.platform_y_mm, 2)],
            "platform_vel": [round(self.platform_vx_mm_s, 2), round(self.platform_vy_mm_s, 2)],
            "platform_acc": [round(self.platform_ax_mm_s2, 2), round(self.platform_ay_mm_s2, 2)],
            "target_pos": [round(self.target_x_mm, 2), round(self.target_y_mm, 2)],
            "cable_lengths_mm": [round(l, 2) for l in self.cable_lengths_mm],
            "cable_rates_mm_s": [round(r, 2) for r in self.cable_rates_mm_s],
            "cable_tensions_N": [round(t, 2) for t in self.cable_tensions_N],
            "motor_speeds_rpm": [round(rpm, 1) for rpm in self.motor_speeds_rpm],
            "motor_torques_Nm": [round(tau, 3) for tau in self.motor_torques_Nm],
            "tracking_error_mm": round(self.tracking_error_mm, 2),
            "controller_mode": self.controller_mode,
            "workspace_safe": self.workspace_safe,
            "collision_safe": self.collision_safe,
            "tension_feasible": self.tension_feasible,
            "solver_converged": self.solver_converged,
            "constraint_residuals_mm": [round(c, 3) for c in self.constraint_residuals_mm],
            "condition_number": round(self.condition_number, 2),
            "active_faults": self.active_faults,
            "trajectory_progress_pct": round(self.trajectory_progress_pct, 1)
        }
