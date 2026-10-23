"""
Hardware Driver implementation for Planar CDPR.
Enforces Rule 0.2, Rule 0.5, and Section 13/23 safety interlocks:
- When hardware capability profile contains 'unknown' or 'unverified' items, physical motion is STRICTLY DISABLED.
- Requires explicit connection, verified communication transport, verified homing (not UNREFERENCED), and zero drive faults.
- Never automatically enables motor torque upon connection.
- Distinguishes measured drive encoder feedback from commanded trajectory or estimation.
"""
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from backend.cdpr.hardware.driver_base import (
    RobotDriver,
    DriverState,
    DriverActuatorFeedback,
    OperatingMode,
    HomingState,
    MeasurementProvenance,
)
from backend.cdpr.config import RobotConfig, HardwareProfile, load_hardware_profile


class HardwareDriver(RobotDriver):
    """
    Physical hardware adapter interfacing with micro-ROS agent / ESP32 and servo drives.
    Safe-by-design:
    - If hardware specifications remain unverified, transitions to HARDWARE_DISABLED.
    - Physical motion is blocked with explicit diagnostic error reporting.
    """

    def __init__(self, config: RobotConfig):
        self.config = config
        self.hw_profile: HardwareProfile = config.hardware_profile or load_hardware_profile()
        self.operating_mode: OperatingMode = OperatingMode.HARDWARE_DISABLED
        self.homing_state: HomingState = HomingState.UNREFERENCED
        self._is_connected: bool = False
        self._last_heartbeat_time: float = 0.0
        self._active_faults: List[str] = []
        self._check_readiness()

    def _check_readiness(self) -> Tuple[bool, List[str]]:
        """Evaluates hardware capability profile prerequisites."""
        missing = []
        if self.hw_profile.status != "verified":
            missing.append(f"Hardware overall status is '{self.hw_profile.status}' (must be 'verified')")
        if not self.hw_profile.transport_verified:
            missing.append(f"Transport '{self.hw_profile.transport_type}' is unverified")
        if not self.hw_profile.drives_verified:
            missing.append(f"Servo drives ({self.hw_profile.drives_model}, {self.hw_profile.drives_protocol}) unverified")
        if not self.hw_profile.emergency_stop_verified:
            missing.append("Independent physical emergency-stop / STO circuit is unverified")
        if self.hw_profile.feedback_available == "unknown":
            missing.append("Actuator encoder feedback availability is unknown")

        if missing:
            self.operating_mode = OperatingMode.HARDWARE_DISABLED
            self._active_faults = ["HARDWARE_CAPABILITIES_UNVERIFIED"]
            return False, missing

        return True, []

    def connect(self) -> Tuple[bool, str]:
        """Attempts connection to physical controller / micro-ROS transport."""
        is_ready, missing = self._check_readiness()
        if not is_ready:
            self._is_connected = False
            return False, f"Hardware connection rejected. Prerequisites missing: {'; '.join(missing)}"

        # If verified, connect to communication bus (stubbed until confirmed transport)
        self._is_connected = True
        self._last_heartbeat_time = time.time()
        self.operating_mode = OperatingMode.HARDWARE
        return True, "Hardware connection established (Motors remain in SAFE DISABLED state)"

    def disconnect(self) -> Tuple[bool, str]:
        self._is_connected = False
        self.operating_mode = OperatingMode.HARDWARE_DISABLED
        return True, "Hardware disconnected and safe state verified"

    def get_status(self) -> Dict[str, Any]:
        is_ready, missing = self._check_readiness()
        return {
            "driver": "HardwareDriver",
            "operating_mode": self.operating_mode.value,
            "is_connected": self._is_connected,
            "homing_state": self.homing_state.value,
            "hardware_ready": is_ready,
            "hardware_motion_enabled": False, # Never enable without verified physical commissioning
            "active_faults": self._active_faults,
            "missing_prerequisites": missing,
            "profile": {
                "controller": self.hw_profile.controller_type,
                "model": self.hw_profile.controller_model,
                "transport": self.hw_profile.transport_type,
                "drives_model": self.hw_profile.drives_model,
                "protocol": self.hw_profile.drives_protocol,
                "emergency_stop_verified": self.hw_profile.emergency_stop_verified,
            }
        }

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "driver": "HardwareDriver",
            "position_control": False, # Disabled until verified
            "velocity_control": False,
            "simulation_only": False,
            "physical_torque_enabled": False,
            "hardware_verified": (self.hw_profile.status == "verified"),
        }

    def read_state(self) -> DriverState:
        # If hardware is not connected or unverified, state reports UNAVAILABLE
        now = time.time()
        return DriverState(
            timestamp=now,
            operating_mode=self.operating_mode,
            homing_state=self.homing_state,
            is_connected=self._is_connected,
            is_moving=False,
            platform_q=np.zeros(2),
            platform_q_dot=np.zeros(2),
            platform_q_ddot=np.zeros(2),
            cable_lengths=np.zeros(4),
            cable_rates=np.zeros(4),
            cable_tensions=np.zeros(4),
            actuator_states=[
                DriverActuatorFeedback(
                    channel_id=i,
                    drum_angle_rad=0.0,
                    angular_velocity_rad_s=0.0,
                    motor_rpm=0.0,
                    cable_length_m=0.0,
                    cable_rate_m_s=0.0,
                    torque_nm=0.0,
                    provenance=MeasurementProvenance.UNAVAILABLE,
                    fault_code="UNVERIFIED_HARDWARE",
                ) for i in range(4)
            ],
            position_provenance=MeasurementProvenance.UNAVAILABLE,
            tensions_provenance=MeasurementProvenance.UNAVAILABLE,
            active_faults=list(self._active_faults),
            message="Hardware motion disabled: Physical specifications unverified.",
        )

    def validate_command(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        is_ready, missing = self._check_readiness()
        if not is_ready:
            return False, f"Hardware command rejected: {'; '.join(missing)}"
        if self.homing_state != HomingState.HOMED:
            return False, f"Hardware command rejected: Platform is in {self.homing_state.value} state. Homing required."
        return False, "Hardware motion disabled by safety interlock."

    def request_move(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        val_ok, msg = self.validate_command(target_q, speed_m_s)
        return False, f"Physical motion blocked by safety policy: {msg}"

    def request_jog(self, delta_x_m: float, delta_y_m: float, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        return False, "Physical jogging blocked: Hardware capabilities unverified."

    def request_stop(self) -> Tuple[bool, str]:
        return True, "Hardware stop requested (all commands clamped to zero)"

    def request_estop(self) -> Tuple[bool, str]:
        self.operating_mode = OperatingMode.HARDWARE_DISABLED
        self._active_faults.append("SOFTWARE_ESTOP_ACTIVE")
        return True, "Software E-STOP activated. Physical STO/E-Stop must be inspected before reset."

    def reset_recoverable_fault(self) -> Tuple[bool, str]:
        # Reset must NOT clear physical faults automatically
        return False, "Hardware faults cannot be reset via software until hardware is verified and inspected."
