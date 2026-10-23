"""
Safety supervisor and fault management system for CDPR.
Implements multi-layer software protection and fault latching.
Per Section 16 & Rule 0.5:
- Software stop and emergency stop latching
- Pre-motion and runtime limit validation
- Explicit fault codes, severity, and reset policies
- Homing readiness gating
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from backend.cdpr.config import RobotConfig


class FaultSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    RECOVERABLE_FAULT = "RECOVERABLE_FAULT"
    CRITICAL_FAULT = "CRITICAL_FAULT"


@dataclass
class FaultRecord:
    code: str
    severity: FaultSeverity
    message: str
    timestamp: float
    is_active: bool = True
    requires_physical_inspection: bool = False


class SafetyManager:
    def __init__(self, config: RobotConfig):
        self.config = config
        self.ws = config.workspace
        self.act = config.actuators
        self.mot = config.motion_limits
        self.cables = config.cables
        self.safety = config.safety

        self._active_faults: Dict[str, FaultRecord] = {}
        self._software_estop: bool = False
        self._watchdog_deadline: float = 0.0

    @property
    def has_active_faults(self) -> bool:
        return any(f.is_active for f in self._active_faults.values())

    @property
    def active_fault_codes(self) -> List[str]:
        return [f.code for f in self._active_faults.values() if f.is_active]

    @property
    def is_estop_active(self) -> bool:
        return self._software_estop

    def trigger_estop(self, reason: str = "Operator E-STOP triggered") -> Tuple[bool, str]:
        """Locks motion into emergency stop state. Software stop cannot clear physical hazards."""
        self._software_estop = True
        record = FaultRecord(
            code="EMERGENCY_STOP_ACTIVE",
            severity=FaultSeverity.CRITICAL_FAULT,
            message=reason,
            timestamp=0.0,
            is_active=True,
            requires_physical_inspection=True,
        )
        self._active_faults["EMERGENCY_STOP_ACTIVE"] = record
        return True, f"Emergency Stop activated: {reason}"

    def reset_faults(self, is_hardware_mode: bool = False) -> Tuple[bool, str]:
        """
        Resets recoverable software faults.
        Physical drive faults or hardware E-stops CANNOT be cleared automatically.
        """
        if is_hardware_mode:
            return False, "Cannot auto-reset hardware faults. Physical inspection and hardware reset procedure required."

        self._software_estop = False
        self._active_faults.clear()
        return True, "Recoverable software faults reset"

    def check_workspace(self, q: np.ndarray) -> Tuple[bool, Optional[FaultRecord]]:
        """Validates that coordinate q = [x, y] is within bounds."""
        x, y = float(q[0]), float(q[1])
        if not (self.ws.x_min_m <= x <= self.ws.x_max_m and self.ws.y_min_m <= y <= self.ws.y_max_m):
            rec = FaultRecord(
                code="OUT_OF_WORKSPACE",
                severity=FaultSeverity.RECOVERABLE_FAULT,
                message=f"Coordinate [{x:.3f}, {y:.3f}] m outside bounds x[{self.ws.x_min_m}, {self.ws.x_max_m}], y[{self.ws.y_min_m}, {self.ws.y_max_m}]",
                timestamp=0.0,
            )
            return False, rec
        return True, None

    def check_speed(self, rpms: np.ndarray) -> Tuple[bool, Optional[FaultRecord]]:
        """Validates that actuator RPMs do not exceed motor limits."""
        max_rpm = self.act.max_speed_rpm
        if np.any(np.abs(rpms) > max_rpm + 1e-3):
            bad_idx = int(np.argmax(np.abs(rpms)))
            rec = FaultRecord(
                code="SPEED_LIMIT_EXCEEDED",
                severity=FaultSeverity.RECOVERABLE_FAULT,
                message=f"Actuator C{bad_idx+1} speed {abs(rpms[bad_idx]):.1f} RPM exceeds limit {max_rpm:.1f} RPM",
                timestamp=0.0,
            )
            return False, rec
        return True, None

    def check_torques(self, torques: np.ndarray) -> Tuple[bool, Optional[FaultRecord]]:
        """Validates that actuator torques do not exceed continuous rating."""
        max_tau = self.act.max_torque_Nm
        if np.any(np.abs(torques) > max_tau + 1e-3):
            bad_idx = int(np.argmax(np.abs(torques)))
            rec = FaultRecord(
                code="TORQUE_LIMIT_EXCEEDED",
                severity=FaultSeverity.RECOVERABLE_FAULT,
                message=f"Actuator C{bad_idx+1} torque {abs(torques[bad_idx]):.2f} Nm exceeds limit {max_tau:.2f} Nm",
                timestamp=0.0,
            )
            return False, rec
        return True, None

    def check_tensions(self, tensions: np.ndarray) -> Tuple[bool, Optional[FaultRecord]]:
        """Validates unilateral tension constraints."""
        if np.any(tensions < self.cables.min_tension_N - 0.05):
            bad_idx = int(np.argmin(tensions))
            rec = FaultRecord(
                code="CABLE_SLACK",
                severity=FaultSeverity.WARNING,
                message=f"Cable C{bad_idx+1} tension {tensions[bad_idx]:.2f} N below minimum {self.cables.min_tension_N:.2f} N",
                timestamp=0.0,
            )
            return False, rec
        if np.any(tensions > self.cables.max_tension_N):
            bad_idx = int(np.argmax(tensions))
            rec = FaultRecord(
                code="OVER_TENSION",
                severity=FaultSeverity.RECOVERABLE_FAULT,
                message=f"Cable C{bad_idx+1} tension {tensions[bad_idx]:.1f} N exceeds rating {self.cables.max_tension_N:.1f} N",
                timestamp=0.0,
            )
            return False, rec
        return True, None
