"""
Simulator Driver implementation for Planar CDPR.
Executes deterministic physics-based simulation loop.
Labels all produced states with MeasurementProvenance.SIMULATED.
Operates fully offline without hardware, ROS 2, or ESP32.
"""
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any
import numpy as np

from backend.cdpr.hardware.driver_base import (
    RobotDriver,
    DriverState,
    DriverActuatorFeedback,
    OperatingMode,
    HomingState,
    MeasurementProvenance,
)
from backend.cdpr.config import RobotConfig

if TYPE_CHECKING:
    from backend.cdpr.simulation import CDPRSimulation


class SimulatorDriver(RobotDriver):
    """
    Simulation driver executing the engineering-grade 2-DOF CDPR digital twin.
    Guaranteed safe: communicates with NO physical hardware.
    """

    def __init__(self, simulation: Any):
        self.sim = simulation
        self.config: RobotConfig = simulation.config
        self._is_connected: bool = True

    def connect(self) -> Tuple[bool, str]:
        self._is_connected = True
        return True, "Simulation driver connected"

    def disconnect(self) -> Tuple[bool, str]:
        self._is_connected = False
        return True, "Simulation driver disconnected"

    def get_status(self) -> Dict[str, Any]:
        return {
            "driver": "SimulatorDriver",
            "operating_mode": OperatingMode.SIMULATION.value,
            "is_connected": self._is_connected,
            "controller_mode": self.sim.controller.mode,
            "sim_time_s": self.sim.sim_time,
            "active_faults": self.sim.controller.active_faults,
            "homing_state": HomingState.HOMED.value,
            "hardware_attached": False,
        }

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "driver": "SimulatorDriver",
            "position_control": True,
            "velocity_control": True,
            "simulation_only": True,
            "physical_torque_enabled": False,
            "hardware_verified": False,
        }

    def read_state(self) -> DriverState:
        telem = self.sim.latest_telemetry
        if telem is None:
            q = self.sim.q
            lengths = self.sim.geom.cable_lengths(q)
            rates = np.zeros(4)
            tensions = np.full(4, self.sim.config.cables.min_tension_N)
        else:
            q = np.array([telem.platform_x_mm / 1000.0, telem.platform_y_mm / 1000.0])
            lengths = np.array(telem.cable_lengths_mm) / 1000.0
            rates = np.array(telem.cable_rates_mm_s) / 1000.0
            tensions = np.array(telem.cable_tensions_N)

        actuator_feedbacks = []
        for i in range(4):
            r = self.config.actuators.drum_radius_m
            rpm = (rates[i] / r) * (60.0 / (2.0 * np.pi)) if r > 0 else 0.0
            tau = (tensions[i] * r) / self.config.actuators.efficiency if r > 0 else 0.0
            actuator_feedbacks.append(
                DriverActuatorFeedback(
                    channel_id=i,
                    drum_angle_rad=lengths[i] / r if r > 0 else 0.0,
                    angular_velocity_rad_s=rates[i] / r if r > 0 else 0.0,
                    motor_rpm=rpm,
                    cable_length_m=lengths[i],
                    cable_rate_m_s=rates[i],
                    torque_nm=tau,
                    provenance=MeasurementProvenance.SIMULATED,
                    fault_code="OK",
                )
            )

        return DriverState(
            timestamp=self.sim.sim_time,
            operating_mode=OperatingMode.SIMULATION,
            homing_state=HomingState.HOMED,
            is_connected=self._is_connected,
            is_moving=(self.sim.controller.mode == "MOVING"),
            platform_q=q,
            platform_q_dot=self.sim.q_dot,
            platform_q_ddot=self.sim.q_ddot,
            cable_lengths=lengths,
            cable_rates=rates,
            cable_tensions=tensions,
            actuator_states=actuator_feedbacks,
            position_provenance=MeasurementProvenance.SIMULATED,
            tensions_provenance=MeasurementProvenance.ESTIMATED,
            active_faults=list(self.sim.controller.active_faults),
            message="Simulation OK",
        )

    def validate_command(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        pts = self.sim.planner.plan_point_to_point(self.sim.q, target_q, v_target=speed_m_s)
        val = self.sim.planner.validate_trajectory(pts)
        if not val.is_feasible:
            return False, f"Move rejected: {val.violation_message} ({val.violation_code})"
        return True, "Target feasible"

    def request_move(self, target_q: np.ndarray, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        return self.sim.controller.request_move(target_q, speed_m_s=speed_m_s)

    def request_jog(self, delta_x_m: float, delta_y_m: float, speed_m_s: Optional[float] = None) -> Tuple[bool, str]:
        return self.sim.controller.request_jog(delta_x_m, delta_y_m, speed_m_s=speed_m_s)

    def request_stop(self) -> Tuple[bool, str]:
        return self.sim.controller.stop()

    def request_estop(self) -> Tuple[bool, str]:
        return self.sim.controller.estop()

    def reset_recoverable_fault(self) -> Tuple[bool, str]:
        self.sim.reset()
        return True, "Simulation state reset to home position"
