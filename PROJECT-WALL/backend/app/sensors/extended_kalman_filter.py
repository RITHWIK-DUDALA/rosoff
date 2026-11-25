"""
Extended Kalman Filter (EKF) State Estimator for PROJECT W.A.L.L.
Implements:
1. Continuous-Discrete Process Model: [x, y, vx, vy]^T (Section 12.1)
2. Nonlinear Cable Length Measurement Function h(x) = [L1, L2, L3, L4]^T
3. Analytical Measurement Jacobian H = [J_L(q), 0_(4x2)]
4. Numerically Stable Joseph-Form Covariance Update P = (I - KH)P^-(I - KH)^T + KRK^T
5. Normalized Innovation Squared (NIS) Statistical Outlier Rejection Test (Section 12.2)
6. Complete Estimator Diagnostics (Section 12.3)
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
import numpy as np

from ..kinematics.cdpr_kinematics import CDPRKinematics


@dataclass
class EKFDiagnostics:
    predicted_state: np.ndarray
    corrected_state: np.ndarray
    covariance_trace: float
    innovation_vector_mm: np.ndarray
    nis_statistic: float
    is_observation_accepted: bool
    estimator_valid: bool


class CDPRExtendedKalmanFilter:
    def __init__(
        self,
        kinematics: CDPRKinematics,
        initial_pos_mm: Tuple[float, float] = (400.0, 300.0),
        process_noise_accel_std: float = 150.0,  # mm/s^2 acceleration random walk
        measurement_noise_std_mm: float = 0.50, # 0.5mm cable encoder resolution noise
        nis_threshold: float = 9.488            # Chi-square 4-DOF at alpha=0.05
    ):
        self.kinematics = kinematics
        self.nis_threshold = nis_threshold

        # State vector: [x (mm), y (mm), vx (mm/s), vy (mm/s)]^T
        self.x = np.array([initial_pos_mm[0], initial_pos_mm[1], 0.0, 0.0], dtype=np.float64)

        # State covariance P (4 x 4)
        self.P = np.diag([25.0, 25.0, 100.0, 100.0]).astype(np.float64)

        # Noise parameters
        self.sigma_a = process_noise_accel_std
        self.sigma_m = measurement_noise_std_mm
        self.R = np.eye(4, dtype=np.float64) * (self.sigma_m ** 2)

        self.accepted_observations_count = 0
        self.rejected_observations_count = 0

    def predict(self, dt: float):
        """
        State Prediction:
        x^- = F * x
        P^- = F * P * F^T + Q
        """
        if dt <= 0.0:
            dt = 0.033

        # State transition matrix F (4 x 4)
        F = np.array([
            [1.0, 0.0, dt,  0.0],
            [0.0, 1.0, 0.0, dt ],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # Continuous white noise discrete process covariance Q (4 x 4)
        dt2 = (dt ** 2) / 2.0
        dt3 = (dt ** 3) / 3.0
        dt4 = (dt ** 4) / 4.0
        q_pos = (self.sigma_a ** 2)

        Q = q_pos * np.array([
            [dt4, 0.0, dt3, 0.0],
            [0.0, dt4, 0.0, dt3],
            [dt3, 0.0, dt2, 0.0],
            [0.0, dt3, 0.0, dt2]
        ], dtype=np.float64)

        # Propagate state and covariance
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, measured_cable_lengths_mm: np.ndarray) -> EKFDiagnostics:
        """
        Measurement Update with Joseph-Form Covariance and NIS Gating:
        z = measured_cable_lengths (4,)
        h(x) = analytical inverse kinematics at (x, y)
        H = [J_L(x, y), 0_(4x2)]
        """
        z = np.asarray(measured_cable_lengths_mm, dtype=np.float64)
        pred_x_copy = self.x.copy()

        # 1. Expected measurement: h(x)
        px, py = self.x[0], self.x[1]
        h_x = self.kinematics.inverse_kinematics(px, py)

        # 2. Measurement residual (innovation)
        r = z - h_x

        # 3. Analytical Measurement Jacobian H (4 x 4)
        J_L, _ = self.kinematics.cable_jacobian(px, py)
        H = np.zeros((4, 4), dtype=np.float64)
        H[:, 0:2] = J_L  # dh/d(pos) = J_L, dh/d(vel) = 0

        # 4. Innovation Covariance S (4 x 4)
        S = H @ self.P @ H.T + self.R

        # 5. Normalized Innovation Squared (NIS) Test (Section 12.2)
        try:
            S_inv = np.linalg.inv(S)
            nis = float(r.T @ S_inv @ r)
        except np.linalg.LinAlgError:
            nis = 999.0
            S_inv = np.linalg.pinv(S)

        is_accepted = bool(nis <= self.nis_threshold)

        if is_accepted:
            self.accepted_observations_count += 1
            # 6. Optimal Kalman Gain K (4 x 4)
            K = self.P @ H.T @ S_inv

            # 7. State Correction
            self.x = self.x + K @ r

            # 8. Joseph-Form Covariance Update (Guarantees symmetry and positive definiteness)
            # P = (I - K*H) * P^- * (I - K*H)^T + K * R * K^T
            I_KH = np.eye(4, dtype=np.float64) - K @ H
            self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T
        else:
            self.rejected_observations_count += 1
            # Do not corrupt state with inconsistent outlier observation

        trace_cov = float(np.trace(self.P))
        valid = bool(trace_cov < 1000.0 and not math.isnan(self.x[0]))

        return EKFDiagnostics(
            predicted_state=pred_x_copy,
            corrected_state=self.x.copy(),
            covariance_trace=round(trace_cov, 4),
            innovation_vector_mm=np.round(r, 4),
            nis_statistic=round(nis, 3),
            is_observation_accepted=is_accepted,
            estimator_valid=valid
        )

    def get_estimated_pose(self) -> Tuple[float, float, float, float]:
        """Returns (x_mm, y_mm, vx_mm_s, vy_mm_s)"""
        return float(self.x[0]), float(self.x[1]), float(self.x[2]), float(self.x[3])

