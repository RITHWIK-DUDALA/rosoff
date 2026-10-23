"""
State estimation and feedback processing module for CDPR.
Implements:
1. Reconstructing platform pose q = [x, y] from redundant measured cable lengths via Forward Kinematics.
2. Residual calculation, Jacobian condition number checking, convergence verification.
3. Tracking error calculation: error = ||q_target - q_estimated|| only when estimate is valid.
4. Staleness detection (stale_timeout_s).
5. Explicit provenance tagging: Commanded, Reported, Estimated, Simulated.
"""
import time
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

from backend.cdpr.kinematics import Kinematics, ForwardKinematicsResult
from backend.cdpr.hardware.driver_base import MeasurementProvenance


@dataclass
class StateEstimateResult:
    timestamp: float
    q_estimated: np.ndarray             # [x, y] in meters
    q_commanded: np.ndarray             # [x, y] in meters
    tracking_error_m: float             # norm of ||q_cmd - q_est||
    tracking_error_valid: bool          # False if estimate is stale, diverged, or unavailable
    residual_norm: float                # norm of ||L(q_est) - L_meas||
    residuals: np.ndarray               # (4,) residuals in meters
    condition_number: float
    is_valid: bool                      # True only if converged & residuals within tolerance
    is_stale: bool
    status_message: str
    provenance: MeasurementProvenance


class StateEstimator:
    def __init__(self, kinematics: Kinematics, stale_timeout_s: float = 0.5):
        self.kin = kinematics
        self.stale_timeout_s = stale_timeout_s
        self.last_valid_estimate: Optional[np.ndarray] = np.zeros(2)
        self.last_update_time: float = 0.0

    def estimate_state(
        self,
        measured_lengths: np.ndarray,
        commanded_q: np.ndarray,
        measurement_timestamp: Optional[float] = None,
        provenance: MeasurementProvenance = MeasurementProvenance.SIMULATED
    ) -> StateEstimateResult:
        """
        Estimates platform position from 4 measured cable lengths.
        Returns StateEstimateResult with validation flags.
        """
        now = time.time() if measurement_timestamp is None else measurement_timestamp
        is_stale = False
        if self.last_update_time > 0 and (now - self.last_update_time) > self.stale_timeout_s:
            is_stale = True

        # Initial guess from last valid estimate or commanded position
        q_init = self.last_valid_estimate if self.last_valid_estimate is not None else commanded_q

        # Execute Forward Kinematics solver
        fk_res: ForwardKinematicsResult = self.kin.forward_kinematics(
            lengths_measured=measured_lengths,
            q_initial=q_init,
            max_iterations=50,
            tolerance=1e-7,
        )

        cmd_q = np.asarray(commanded_q, dtype=np.float64).reshape(2)

        if fk_res.converged and fk_res.residual_norm <= 0.02:  # <= 20 mm residual tolerance
            q_est = fk_res.q_estimated
            self.last_valid_estimate = q_est.copy()
            self.last_update_time = now
            tracking_err = float(np.linalg.norm(cmd_q - q_est))
            tracking_valid = not is_stale

            return StateEstimateResult(
                timestamp=now,
                q_estimated=q_est,
                q_commanded=cmd_q,
                tracking_error_m=tracking_err,
                tracking_error_valid=tracking_valid,
                residual_norm=fk_res.residual_norm,
                residuals=fk_res.residuals,
                condition_number=fk_res.condition_number,
                is_valid=True,
                is_stale=is_stale,
                status_message="Valid Estimate" if not is_stale else "STALE_ESTIMATE",
                provenance=provenance,
            )
        else:
            return StateEstimateResult(
                timestamp=now,
                q_estimated=np.full(2, np.nan),
                q_commanded=cmd_q,
                tracking_error_m=float("nan"),
                tracking_error_valid=False,
                residual_norm=fk_res.residual_norm,
                residuals=fk_res.residuals,
                condition_number=fk_res.condition_number,
                is_valid=False,
                is_stale=is_stale,
                status_message=f"FK Diverged: {fk_res.message}",
                provenance=MeasurementProvenance.UNAVAILABLE,
            )
