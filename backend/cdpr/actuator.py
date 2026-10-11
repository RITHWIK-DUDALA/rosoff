"""
Actuator model for CDPR winches/servos.
Simulates:
- Drum spooling geometry: L = r * theta, v_cable = r * omega
- Sign convention:
    Positive cable payout rate (dL/dt > 0) -> drum rotation in unspooling direction (+omega)
    Retraction rate (dL/dt < 0) -> drum rotation in spooling direction (-omega)
- Motor RPM: RPM = (60 / 2*pi) * omega = (60 / (2*pi*r)) * L_dot
- Estimated motor torque: tau = (T * r) / efficiency + J_drum * alpha + b_fric * omega
- Hard provisional limits:
    Speed saturation at 300 RPM
    Torque saturation at 0.4 Nm
"""
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from backend.cdpr.config import RobotConfig


@dataclass
class ServoChannelState:
    channel_id: int             # 0..3 (C1..C4)
    target_drum_angle_rad: float
    actual_drum_angle_rad: float
    target_angular_vel_rad_s: float
    actual_angular_vel_rad_s: float
    motor_rpm: float
    cable_length_m: float
    cable_rate_m_s: float
    cable_tension_N: float
    estimated_torque_Nm: float
    speed_saturated: bool
    torque_saturated: bool
    fault_code: str             # "OK", "SPEED_LIMIT", "TORQUE_LIMIT", "CABLE_SLACK"


class ActuatorArray:
    def __init__(self, config: RobotConfig):
        self.config = config
        self.act_cfg = config.actuators
        self.r = self.act_cfg.drum_radius_m
        self.max_rpm = self.act_cfg.max_speed_rpm
        self.max_omega = self.act_cfg.max_speed_rad_s
        self.max_tau = self.act_cfg.max_torque_Nm
        self.eff = self.act_cfg.efficiency
        self.J_drum = self.act_cfg.drum_inertia_kg_m2
        self.dt = config.simulation.timestep_s

        # Initial reference lengths at origin
        # Internal states: drum angles in radians
        self.drum_angles = np.zeros(4, dtype=np.float64)
        self.drum_velocities = np.zeros(4, dtype=np.float64)
        self.prev_lengths = np.zeros(4, dtype=np.float64)
        self.initialized = False

    def reset(self, initial_lengths: np.ndarray):
        """Initializes winch drum angles based on initial cable lengths."""
        self.prev_lengths = np.asarray(initial_lengths, dtype=np.float64).copy()
        # Define zero angle at initial assembly length
        self.drum_angles = np.zeros(4, dtype=np.float64)
        self.drum_velocities = np.zeros(4, dtype=np.float64)
        self.initialized = True

    def calculate_rpm(self, cable_rates_m_s: np.ndarray) -> np.ndarray:
        """
        Converts cable velocity (m/s) to motor RPM.
        v = omega * r => omega = v / r
        RPM = omega * 60 / (2 * pi)
        """
        omega = cable_rates_m_s / self.r
        return omega * (60.0 / (2.0 * np.pi))

    def update(
        self,
        current_lengths: np.ndarray,
        cable_rates: np.ndarray,
        cable_tensions: np.ndarray,
        cable_accelerations: np.ndarray = None
    ) -> List[ServoChannelState]:
        """
        Updates actuator states for timestep dt.
        current_lengths: (4,) in meters
        cable_rates: (4,) in m/s (L_dot)
        cable_tensions: (4,) in N
        cable_accelerations: optional (4,) in m/s^2 (L_ddot)
        """
        if not self.initialized:
            self.reset(current_lengths)

        if cable_accelerations is None:
            cable_accelerations = np.zeros(4, dtype=np.float64)

        # Angular velocity demand: omega = L_dot / r
        omega_demanded = cable_rates / self.r
        alpha_demanded = cable_accelerations / self.r

        states = []
        for i in range(4):
            w_tgt = omega_demanded[i]
            # Check speed saturation
            is_speed_sat = abs(w_tgt) > self.max_omega
            w_actual = np.clip(w_tgt, -self.max_omega, self.max_omega)

            # Integrate drum angle: theta[k] = theta[k-1] + w_actual * dt
            self.drum_angles[i] += w_actual * self.dt
            self.drum_velocities[i] = w_actual

            rpm_actual = w_actual * (60.0 / (2.0 * np.pi))

            # Motor torque calculation:
            # tau_motor = (T * r) / efficiency + J_drum * alpha
            T_i = max(0.0, float(cable_tensions[i]))
            tau_ideal = (T_i * self.r) / self.eff
            tau_inertia = self.J_drum * alpha_demanded[i]
            tau_total = tau_ideal + tau_inertia

            is_tau_sat = tau_total > self.max_tau

            fault = "OK"
            if is_speed_sat:
                fault = "SPEED_LIMIT"
            elif is_tau_sat:
                fault = "TORQUE_LIMIT"
            elif T_i < self.config.cables.min_tension_N:
                fault = "CABLE_SLACK"

            state = ServoChannelState(
                channel_id=i,
                target_drum_angle_rad=float(self.drum_angles[i]),
                actual_drum_angle_rad=float(self.drum_angles[i]),
                target_angular_vel_rad_s=float(w_tgt),
                actual_angular_vel_rad_s=float(w_actual),
                motor_rpm=float(rpm_actual),
                cable_length_m=float(current_lengths[i]),
                cable_rate_m_s=float(cable_rates[i]),
                cable_tension_N=float(T_i),
                estimated_torque_Nm=float(tau_total),
                speed_saturated=is_speed_sat,
                torque_saturated=is_tau_sat,
                fault_code=fault
            )
            states.append(state)

        self.prev_lengths = current_lengths.copy()
        return states
