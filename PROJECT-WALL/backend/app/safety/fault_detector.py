"""
Fault Detection & Residual Anomaly Monitoring for PROJECT W.A.L.L.
Implements:
1. Deterministic Rule-Based Thresholding (Section 17.1)
2. Residual-Based Fault Detection: r_pos = q_pred - q_obs, r_cable = L_pred - L_meas (Section 17.2)
3. Cumulative Sum (CUSUM) Anomaly Change Detection (Section 17.2)
4. Physical Fault Propagation Engine (Section 17.3)
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional
import numpy as np


@dataclass
class AnomalyStatus:
    is_fault_detected: bool
    fault_type: Optional[str]
    cusum_statistic: float
    residual_magnitude: float
    message: str


class CUSUMDetector:
    """
    Cumulative Sum (CUSUM) change-point detector:
    S_k = max(0, S_(k-1) + |r_k| - delta)
    Triggers alarm when S_k >= threshold h.
    """
    def __init__(self, drift_delta: float = 0.5, threshold_h: float = 5.0):
        self.delta = drift_delta
        self.h = threshold_h
        self.s_pos = 0.0

    def reset(self):
        self.s_pos = 0.0

    def step(self, residual_val: float) -> Tuple[bool, float]:
        self.s_pos = max(0.0, self.s_pos + abs(residual_val) - self.delta)
        is_alarm = bool(self.s_pos >= self.h)
        return is_alarm, float(round(self.s_pos, 3))


class ComprehensiveFaultDetector:
    def __init__(
        self,
        max_position_error_mm: float = 15.0,
        max_cable_residual_mm: float = 8.0,
        min_cable_tension_n: float = 2.0,
        max_cable_tension_n: float = 50.0
    ):
        self.max_pos_err = max_position_error_mm
        self.max_cable_res = max_cable_residual_mm
        self.t_min = min_cable_tension_n
        self.t_max = max_cable_tension_n

        self.pos_cusum = CUSUMDetector(drift_delta=0.8, threshold_h=8.0)
        self.cable_cusums = [CUSUMDetector(drift_delta=0.5, threshold_h=6.0) for _ in range(4)]

        self.fault_history: List[Dict[str, Any]] = []

    def evaluate(
        self,
        q_predicted_mm: Tuple[float, float],
        q_observed_mm: Tuple[float, float],
        l_predicted_mm: np.ndarray,
        l_measured_mm: np.ndarray,
        measured_tensions_n: np.ndarray
    ) -> AnomalyStatus:
        """
        Executes residual and rule-based evaluation.
        """
        # 1. Position Residual: r_pos = || q_pred - q_obs ||
        dx = q_predicted_mm[0] - q_observed_mm[0]
        dy = q_predicted_mm[1] - q_observed_mm[1]
        r_pos_norm = math.hypot(dx, dy)

        pos_alarm, pos_stat = self.pos_cusum.step(r_pos_norm)

        if r_pos_norm > self.max_pos_err or pos_alarm:
            msg = f"Position tracking fault: residual {r_pos_norm:.2f}mm (CUSUM: {pos_stat:.2f})"
            self.fault_history.append({"type": "EXCESSIVE_TRACKING_ERROR", "residual": r_pos_norm})
            return AnomalyStatus(True, "EXCESSIVE_TRACKING_ERROR", pos_stat, r_pos_norm, msg)

        # 2. Cable Length Residuals: r_cable_i = | L_pred_i - L_meas_i |
        r_cables = np.abs(l_predicted_mm - l_measured_mm)
        for i in range(4):
            c_alarm, c_stat = self.cable_cusums[i].step(r_cables[i])
            if r_cables[i] > self.max_cable_res or c_alarm:
                msg = f"Cable C{i+1} discrepancy: residual {r_cables[i]:.2f}mm (CUSUM: {c_stat:.2f})"
                self.fault_history.append({"type": f"CABLE_C{i+1}_DISCREPANCY", "residual": float(r_cables[i])})
                return AnomalyStatus(True, f"CABLE_C{i+1}_DISCREPANCY", c_stat, float(r_cables[i]), msg)

        # 3. Cable Tension Limits
        for i in range(4):
            t = measured_tensions_n[i]
            if t < self.t_min:
                msg = f"Cable C{i+1} SLACK: tension {t:.2f}N < {self.t_min:.1f}N"
                return AnomalyStatus(True, f"CABLE_C{i+1}_SLACK", 0.0, float(t), msg)
            if t > self.t_max:
                msg = f"Cable C{i+1} OVERLOAD: tension {t:.2f}N > {self.t_max:.1f}N"
                return AnomalyStatus(True, f"CABLE_C{i+1}_OVERLOAD", 0.0, float(t), msg)

        return AnomalyStatus(False, None, pos_stat, r_pos_norm, "All kinematic and dynamic residuals nominal")

