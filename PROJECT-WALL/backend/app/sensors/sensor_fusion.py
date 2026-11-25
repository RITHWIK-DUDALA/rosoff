"""
Sensor Models & Multi-Sensor State Estimation for PROJECT W.A.L.L.
Implements simulated hardware transducers:
- Optical incremental encoders (2048 CPR)
- 6-DOF IMU (accelerometer & gyroscope on end-effector)
- Optical TOF laser distance sensor (standoff measurement)
- S-beam load cell tension sensors
- Complementary Filter for fused pose & tilt estimation (Section 7.2)
"""

import time
import math
import random
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class IMUReading:
    accel_x_mps2: float
    accel_y_mps2: float
    accel_z_mps2: float
    gyro_z_radps: float
    platform_tilt_deg: float


@dataclass
class StandoffReading:
    measured_gap_mm: float
    is_valid: bool
    signal_confidence: float


class EndEffectorSensorSuite:
    def __init__(self, target_standoff_mm: float = 2.0):
        self.target_standoff_mm = target_standoff_mm
        self.current_standoff_mm = target_standoff_mm

        # Filter state
        self.fused_x_mm: float = 400.0
        self.fused_y_mm: float = 300.0
        self.fused_vx_mps: float = 0.0
        self.fused_vy_mps: float = 0.0
        self.platform_tilt_deg: float = 0.0

        # Sensor noise settings
        self.encoder_noise_std_mm: float = 0.02
        self.tof_noise_std_mm: float = 0.05
        self.imu_accel_noise_mps2: float = 0.05

    def read_imu(self, true_ax_mps2: float = 0.0, true_ay_mps2: float = 0.0) -> IMUReading:
        # Gravity acts along -Y (assuming vertical wall mounting)
        # Accelerometer reads -9.81 on Y when static
        ax = true_ax_mps2 + random.gauss(0.0, self.imu_accel_noise_mps2)
        ay = true_ay_mps2 - 9.81 + random.gauss(0.0, self.imu_accel_noise_mps2)
        az = random.gauss(0.0, 0.02) # minimal out-of-plane

        # Tilt angle relative to vertical
        tilt = math.degrees(math.atan2(ax, -ay))
        self.platform_tilt_deg = tilt

        return IMUReading(
            accel_x_mps2=round(ax, 3),
            accel_y_mps2=round(ay, 3),
            accel_z_mps2=round(az, 3),
            gyro_z_radps=round(random.gauss(0.0, 0.01), 3),
            platform_tilt_deg=round(tilt, 2)
        )

    def read_standoff(self, surface_roughness: float = 0.05) -> StandoffReading:
        # Distance variation modeled from substrate roughness
        gap = self.current_standoff_mm + random.gauss(0.0, self.tof_noise_std_mm + surface_roughness * 0.1)
        valid = (0.5 <= gap <= 5.0)
        confidence = 0.98 if valid else 0.40

        return StandoffReading(
            measured_gap_mm=round(gap, 3),
            is_valid=valid,
            signal_confidence=confidence
        )

    def update_fusion(
        self,
        fk_x_mm: float,
        fk_y_mm: float,
        dt: float,
        measured_ax_mps2: float = 0.0,
        measured_ay_mps2: float = 0.0
    ) -> Tuple[float, float]:
        """
        Complementary Filter:
        Blends low-frequency kinematics (from cable lengths) with high-frequency IMU acceleration.
        """
        alpha = 0.92  # Weight given to kinematics position

        # Accelerometer integration (converting m/s^2 to mm/s^2 by *1000)
        pred_x = self.fused_x_mm + (self.fused_vx_mps * 1000.0) * dt + 0.5 * (measured_ax_mps2 * 1000.0) * (dt ** 2)
        pred_y = self.fused_y_mm + (self.fused_vy_mps * 1000.0) * dt + 0.5 * (measured_ay_mps2 * 1000.0) * (dt ** 2)

        self.fused_x_mm = alpha * fk_x_mm + (1.0 - alpha) * pred_x
        self.fused_y_mm = alpha * fk_y_mm + (1.0 - alpha) * pred_y

        self.fused_vx_mps = (self.fused_x_mm - fk_x_mm) / (dt * 1000.0) if dt > 0 else 0.0
        self.fused_vy_mps = (self.fused_y_mm - fk_y_mm) / (dt * 1000.0) if dt > 0 else 0.0

        return self.fused_x_mm, self.fused_y_mm

