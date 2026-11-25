"""
Four Motorized Winch Assemblies Module for PROJECT W.A.L.L.
Implements the 4 independent motorized winch units (M1, M2, M3, M4),
multilayer drum winding model, encoder tick accumulation, and PID velocity/position control
as specified in Part 4 of the Specification.
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class MotorStatus(str, Enum):
    DISABLED = "DISABLED"
    UNINITIALIZED = "UNINITIALIZED"
    HOMING = "HOMING"
    READY = "READY"
    MOVING = "MOVING"
    HOLDING = "HOLDING"
    WARNING = "WARNING"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class DrumGeometry:
    core_radius_mm: float = 10.0          # r0 = 10 mm
    drum_width_mm: float = 25.0
    flange_diameter_mm: float = 40.0
    cable_diameter_mm: float = 1.0        # Dyneema / UHMWPE 1mm
    max_layers: int = 4
    cable_capacity_m: float = 3.5

    def effective_radius_mm(self, wound_cable_length_mm: float) -> float:
        """
        Multilayer drum winding radius calculation (Section 4.3):
        Effective radius increases as cable wraps accumulate.
        """
        circumference = 2.0 * math.pi * self.core_radius_mm
        wraps_per_layer = max(1.0, self.drum_width_mm / self.cable_diameter_mm)
        cable_per_layer = wraps_per_layer * circumference

        current_layer = min(self.max_layers - 1, int(wound_cable_length_mm / cable_per_layer))
        return self.core_radius_mm + (current_layer * self.cable_diameter_mm * 0.866)


@dataclass
class MotorSpecifications:
    rated_voltage_v: float = 24.0
    rated_torque_nm: float = 0.45
    peak_torque_nm: float = 1.20
    max_rpm: float = 350.0
    gear_ratio: float = 1.0               # Direct drive or 1:1 planetary
    encoder_cpr: int = 4096               # 4096 counts per revolution


class WinchMotor:
    def __init__(
        self,
        motor_id: str,
        name: str,
        drum: Optional[DrumGeometry] = None,
        specs: Optional[MotorSpecifications] = None
    ):
        self.motor_id = motor_id
        self.name = name
        self.drum = drum or DrumGeometry()
        self.specs = specs or MotorSpecifications()

        # Operational state
        self.status: MotorStatus = MotorStatus.READY
        self.angle_rad: float = 0.0              # Current shaft angle
        self.commanded_angle_rad: float = 0.0    # Target shaft angle
        self.angular_velocity_rad_s: float = 0.0 # Current speed
        self.commanded_velocity_rad_s: float = 0.0
        self.torque_nm: float = 0.0
        self.current_a: float = 0.0
        self.temperature_c: float = 28.5

        # Stored cable on drum
        self.stored_cable_length_mm: float = 1200.0  # Initial wound cable stored
        self.encoder_ticks: int = 0
        self.fault_code: Optional[str] = None

        # Shaft PID position controller
        self.kp = 12.0
        self.ki = 0.2
        self.kd = 0.5
        self.integral_err = 0.0
        self.last_err = 0.0

    @property
    def speed_rpm(self) -> float:
        """Current motor rotational velocity in revolutions per minute (RPM)"""
        return float((self.angular_velocity_rad_s * 60.0) / (2.0 * math.pi))

    def compute_cable_delta_from_rotation(self, delta_theta_rad: float) -> float:
        """
        Calculates cable length change from drum rotation (Section 4.4):
        delta_L = r_eff * delta_theta
        """
        r_eff = self.drum.effective_radius_mm(self.stored_cable_length_mm)
        delta_l = r_eff * delta_theta_rad
        return delta_l

    def compute_rotation_from_cable_delta(self, delta_length_mm: float) -> float:
        """
        Inverse winding: delta_theta = delta_L / r_eff
        """
        r_eff = self.drum.effective_radius_mm(self.stored_cable_length_mm)
        return delta_length_mm / r_eff

    def step(self, commanded_len_delta_mm: float, dt: float, cable_tension_n: float = 10.0) -> float:
        """
        Simulates motor shaft rotation over timestep dt.
        Returns the actual cable length change delivered in mm.
        """
        if self.status in (MotorStatus.FAULT, MotorStatus.EMERGENCY_STOP, MotorStatus.DISABLED):
            self.angular_velocity_rad_s = 0.0
            return 0.0

        # Target shaft angle increment
        target_delta_theta = self.compute_rotation_from_cable_delta(commanded_len_delta_mm)
        desired_w = target_delta_theta / dt if dt > 0 else 0.0

        # Maximum velocity limit (RPM to rad/s)
        max_w = (self.specs.max_rpm * 2.0 * math.pi) / 60.0
        desired_w = max(-max_w, min(max_w, desired_w))

        # PID position tracking error
        err = target_delta_theta
        self.integral_err += err * dt
        deriv = (err - self.last_err) / dt if dt > 0 else 0.0
        self.last_err = err

        output_w = (self.kp * err) + (self.ki * self.integral_err) + (self.kd * deriv)
        actual_w = max(-max_w, min(max_w, output_w))
        self.angular_velocity_rad_s = actual_w

        # Integrate shaft rotation
        d_theta = actual_w * dt
        self.angle_rad += d_theta

        # Update encoder ticks
        self.encoder_ticks += int((d_theta / (2.0 * math.pi)) * self.specs.encoder_cpr)

        # Actual cable length released (positive = payout/unwind, negative = reel-in/wind)
        actual_delta_l = self.compute_cable_delta_from_rotation(d_theta)
        self.stored_cable_length_mm = max(0.0, self.stored_cable_length_mm - actual_delta_l)

        # Torque and electrical current estimation: Torque = Tension * r_eff
        r_m = self.drum.effective_radius_mm(self.stored_cable_length_mm) / 1000.0
        self.torque_nm = cable_tension_n * r_m
        self.current_a = min(3.0, (self.torque_nm / max(0.01, self.specs.rated_torque_nm)) * 1.5)

        # Thermal dissipation
        self.temperature_c = min(75.0, 25.0 + (self.current_a ** 2) * 2.5)

        # Motor status
        if abs(actual_w) > 0.01:
            self.status = MotorStatus.MOVING
        else:
            self.status = MotorStatus.HOLDING

        return actual_delta_l

    def trip_fault(self, code: str):
        self.status = MotorStatus.FAULT
        self.fault_code = code

    def reset(self):
        self.status = MotorStatus.READY
        self.fault_code = None
        self.integral_err = 0.0
        self.last_err = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motor_id": str(self.motor_id),
            "name": str(self.name),
            "status": str(self.status.value),
            "angle_deg": float(round(math.degrees(self.angle_rad), 2)),
            "speed_rpm": float(round((float(self.angular_velocity_rad_s) * 60.0) / (2.0 * math.pi), 1)),
            "torque_nm": float(round(self.torque_nm, 3)),
            "current_a": float(round(self.current_a, 2)),
            "temperature_c": float(round(self.temperature_c, 1)),
            "encoder_ticks": int(self.encoder_ticks),
            "effective_drum_radius_mm": float(round(self.drum.effective_radius_mm(self.stored_cable_length_mm), 2)),
            "fault": str(self.fault_code) if self.fault_code else None
        }

