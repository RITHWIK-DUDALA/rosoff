"""
Cascaded Control Subsystem for PROJECT W.A.L.L.
Implements:
1. Outer Loop: 2-DOF Cartesian Position PID Tracking with Anti-Windup (Section 10.2)
2. Middle Loop: Cable Length Velocity Reference Generation via Jacobian: L_dot = J_L(q) * q_dot (Section 10.3)
3. Model-based Feedforward Cable Tension & Rate Mapping (Section 10.4)
4. Tracking Diagnostics & Performance Metrics (Section 10.5)
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
import numpy as np

from ..kinematics.cdpr_kinematics import CDPRKinematics


@dataclass
class PIDParameters:
    kp: float = 4.5           # Proportional gain (1/s)
    ki: float = 0.8           # Integral gain (1/s^2)
    kd: float = 0.25          # Derivative gain
    anti_windup_limit: float = 50.0  # mm clamp for integral accumulator
    max_output_velocity_mm_s: float = 120.0 # Maximum commanded Cartesian speed


@dataclass
class ControllerTrackingMetrics:
    rms_error_mm: float
    max_error_mm: float
    steady_state_error_mm: float
    is_saturated: bool


class CascadedCDPRController:
    def __init__(self, kinematics: CDPRKinematics, pid_params: Optional[PIDParameters] = None):
        self.kinematics = kinematics
        self.pid = pid_params or PIDParameters()

        # State tracking
        self.integral_error = np.zeros(2, dtype=np.float64) # [int_ex, int_ey]
        self.prev_error = np.zeros(2, dtype=np.float64)
        self.history_errors: list = []

    def reset(self):
        self.integral_error.fill(0.0)
        self.prev_error.fill(0.0)
        self.history_errors.clear()

    def update(
        self,
        target_pos_mm: Tuple[float, float],
        target_vel_mm_s: Tuple[float, float],
        actual_pos_mm: Tuple[float, float],
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray, ControllerTrackingMetrics]:
        """
        Executes one control cycle:
        1. Outer loop calculates Cartesian commanded velocity:
           v_cmd = v_ff + Kp * e + Ki * int(e) + Kd * de/dt
        2. Middle loop translates Cartesian velocity to cable length rates:
           L_dot_cmd = J_L(q) * v_cmd
        Returns:
            (v_cartesian_cmd, cable_rates_cmd_mm_s, metrics)
        """
        if dt <= 0.0:
            dt = 0.033

        target_p = np.array(target_pos_mm, dtype=np.float64)
        target_v = np.array(target_vel_mm_s, dtype=np.float64)
        actual_p = np.array(actual_pos_mm, dtype=np.float64)

        # 1. Position error: e = target - actual
        error = target_p - actual_p
        error_norm = float(np.linalg.norm(error))
        self.history_errors.append(error_norm)

        # Integral term with anti-windup clamping
        self.integral_error += error * dt
        for i in range(2):
            self.integral_error[i] = float(np.clip(
                self.integral_error[i],
                -self.pid.anti_windup_limit,
                self.pid.anti_windup_limit
            ))

        # Derivative term
        d_error = (error - self.prev_error) / dt
        self.prev_error = error.copy()

        # Feedback correction
        v_feedback = (
            self.pid.kp * error +
            self.pid.ki * self.integral_error +
            self.pid.kd * d_error
        )

        # Cascaded Cartesian command with feedforward
        v_cmd_raw = target_v + v_feedback

        # Velocity saturation check
        v_cmd_mag = float(np.linalg.norm(v_cmd_raw))
        is_saturated = False
        if v_cmd_mag > self.pid.max_output_velocity_mm_s:
            v_cartesian_cmd = (v_cmd_raw / v_cmd_mag) * self.pid.max_output_velocity_mm_s
            is_saturated = True
        else:
            v_cartesian_cmd = v_cmd_raw

        # 2. Kinematic mapping: L_dot = J_L(q) * v_cmd
        J, _ = self.kinematics.cable_jacobian(actual_p[0], actual_p[1])
        cable_rates_cmd_mm_s = J @ v_cartesian_cmd  # (4,) cable length rates

        # 3. Compute tracking metrics (Section 10.5)
        recent = self.history_errors[-50:] if len(self.history_errors) >= 50 else self.history_errors
        rms_err = float(np.sqrt(np.mean(np.square(recent))))
        max_err = float(np.max(recent))
        steady_state = float(np.mean(recent[-10:])) if len(recent) >= 10 else error_norm

        metrics = ControllerTrackingMetrics(
            rms_error_mm=round(rms_err, 4),
            max_error_mm=round(max_err, 4),
            steady_state_error_mm=round(steady_state, 4),
            is_saturated=is_saturated
        )

        return v_cartesian_cmd, cable_rates_cmd_mm_s, metrics

