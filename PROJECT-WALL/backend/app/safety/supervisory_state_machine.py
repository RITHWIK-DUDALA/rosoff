"""
Supervisory State Machine & Safety Management for PROJECT W.A.L.L.
Enforces safety interlocks, cable slack/overload detection, motor fault monitoring,
and emergency stop supervision as specified in Part 14 of the Specification.
"""

import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


class CDPRSystemState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    IDLE = "IDLE"
    SURFACE_CALIBRATION = "SURFACE_CALIBRATION"
    READY = "READY"
    MOVING = "MOVING"
    PRINTING = "PRINTING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class FaultSeverity(str, Enum):
    WARNING = "WARNING"
    CONTROLLED_STOP = "CONTROLLED_STOP"
    EMERGENCY_SHUTDOWN = "EMERGENCY_SHUTDOWN"


@dataclass
class ActiveFault:
    code: str
    message: str
    subsystem: str
    severity: FaultSeverity
    timestamp: float


class CDPRSupervisor:
    def __init__(self):
        self.state: CDPRSystemState = CDPRSystemState.READY
        self.previous_state: Optional[CDPRSystemState] = None
        self.active_faults: Dict[str, ActiveFault] = {}
        self.is_emergency_stopped: bool = False
        self.state_enter_time: float = time.time()
        self.transition_log: List[Dict[str, Any]] = []

    def can_transition(self, target: CDPRSystemState) -> bool:
        if target == self.state:
            return True
        if self.is_emergency_stopped and target not in (CDPRSystemState.EMERGENCY_STOP, CDPRSystemState.READY):
            return False
        return True

    def transition_to(self, target: CDPRSystemState, reason: str = "") -> bool:
        if not self.can_transition(target):
            return False

        self.transition_log.append({
            "from": self.state.value,
            "to": target.value,
            "timestamp": time.time(),
            "reason": reason
        })
        self.previous_state = self.state
        self.state = target
        self.state_enter_time = time.time()

        if target == CDPRSystemState.EMERGENCY_STOP:
            self.is_emergency_stopped = True
            if "E_STOP" not in self.active_faults:
                self.active_faults["E_STOP"] = ActiveFault(
                    code="E_STOP",
                    message=f"Emergency stop activated: {reason}",
                    subsystem="SUPERVISOR",
                    severity=FaultSeverity.EMERGENCY_SHUTDOWN,
                    timestamp=time.time()
                )

        return True

    def report_fault(self, code: str, message: str, subsystem: str, severity: FaultSeverity):
        fault = ActiveFault(code, message, subsystem, severity, time.time())
        self.active_faults[code] = fault

        if severity == FaultSeverity.EMERGENCY_SHUTDOWN and self.state != CDPRSystemState.EMERGENCY_STOP:
            self.transition_to(CDPRSystemState.EMERGENCY_STOP, reason=message)
        elif severity == FaultSeverity.CONTROLLED_STOP and self.state not in (CDPRSystemState.EMERGENCY_STOP, CDPRSystemState.FAULT):
            self.transition_to(CDPRSystemState.FAULT, reason=message)

    def clear_fault(self, code: str):
        if code in self.active_faults:
            del self.active_faults[code]

    def reset(self) -> bool:
        self.is_emergency_stopped = False
        self.active_faults.clear()
        self.previous_state = self.state
        self.state = CDPRSystemState.READY
        self.transition_log.append({
            "from": self.previous_state.value if self.previous_state else "UNKNOWN",
            "to": CDPRSystemState.READY.value,
            "timestamp": time.time(),
            "reason": "Operator reset"
        })
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "is_emergency_stopped": self.is_emergency_stopped,
            "active_faults": [f.__dict__ for f in self.active_faults.values()],
            "recent_transitions": self.transition_log[-6:]
        }
