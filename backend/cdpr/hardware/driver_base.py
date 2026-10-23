"""
Hardware Abstraction Layer (HAL) base interface for Planar CDPR.
Defines common driver contract for both SimulatorDriver and HardwareDriver.
Enforces explicit measurement provenance: 'simulated' vs 'measured' vs 'estimated'.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class OperatingMode(str, Enum):
    SIMULATION = "SIMULATION"
    HARDWARE = "HARDWARE"
    HARDWARE_DISABLED = "HARDWARE_DISABLED"


class HomingState(str, Enum):
    UNREFERENCED = "UNREFERENCED"
    HOMING_IN_PROGRESS = "HOMING_IN_PROGRESS"
    HOMED = "HOMED"
    FAULT = "FAULT"


class MeasurementProvenance(str, Enum):
    SIMULATED = "simulated"
    MEASURED = "measured"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


@dataclass
class DriverActuatorFeedback:
    channel_id: int
    drum_angle_rad: float
    angular_velocity_rad_s: float
    motor_rpm: float
    cable_length_m: float
    cable_rate_m_s: float
    torque_nm: float
    provenance: MeasurementProvenance
    fault_code: str = "OK"


@dataclass
class DriverState:
    timestamp: float
    operating_mode: OperatingMode
    homing_state: HomingState
    is_connected: bool
    is_moving: bool
    platform_q: np.ndarray             # [x, y] in meters
    platform_q_dot: np.ndarray         # [vx, vy] in m/s
    platform_q_ddot: np.ndarray        # [ax, ay] in m/s^2
    cable_lengths: np.ndarray          # 4-element array in meters
    cable_rates: np.ndarray            # 4-element array in m/s
    cable_tensions: np.ndarray         # 4-element array in N
    actuator_states: List[DriverActuatorFeedback] = field(default_factory=list)
    position_provenance: MeasurementProvenance = MeasurementProvenance.SIMULATED
    tensions_provenance: MeasurementProvenance = MeasurementProvenance.ESTIMATED
    active_faults: List[str] = field(default_factory=list)
    message: str = "OK"


class RobotDriver(ABC):
    """Abstract base class for all CDPR robot drivers."""

    @abstractmethod
    def connect(self) -> Tuple[bool, str]:
        """Establishes connection to the robot backend or hardware interface."""
        pass

    @abstractmethod
    def disconnect(self) -> Tuple[bool, str]:
        """Safely disconnects driver, ensuring motors enter safe state."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns detailed driver status, connection, and health diagnostics."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Returns hardware verification profile and enabled features."""
        pass

    @abstractmethod
    def read_state(self) -> DriverState:
        """Reads latest state with explicit measurement provenance."""
        pass

    @abstractmethod
    def validate_command(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        """Validates target coordinates and speed against workspace and safety limits."""
        pass

    @abstractmethod
    def request_move(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        """Executes move to target position."""
        pass

    @abstractmethod
    def request_jog(self, delta_x_m: float, delta_y_m: float, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        """Executes jog increment."""
        pass

    @abstractmethod
    def request_stop(self) -> Tuple[bool, str]:
        """Requests controlled decelerated stop (highest priority within software)."""
        pass

    @abstractmethod
    def request_estop(self) -> Tuple[bool, str]:
        """Requests software emergency stop and locks motion."""
        pass

    @abstractmethod
    def reset_recoverable_fault(self) -> Tuple[bool, str]:
        """Resets recoverable software state (does NOT clear physical drive faults)."""
        pass
