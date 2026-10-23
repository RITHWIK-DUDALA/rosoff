"""
End-to-End Automated Simulation Test (Section 18.7 of Master Specification).
Workflow:
1. Initialize CDPR simulation backend with canonical configuration.
2. Verify SimulatorDriver is active and HardwareDriver is not activated.
3. Submit a valid Cartesian move target [0.060, 0.040] m ([60, 40] mm).
4. Verify trajectory generation and pre-motion feasibility checks.
5. Deterministically advance the physics simulation loop until arrival.
6. Obtain updated cable lengths from kinematics and actuator winches.
7. Reconstruct estimated platform position using forward kinematics least-squares solver.
8. Compare estimated position to target position (acceptable numerical tolerance < 1.0 mm).
9. Confirm all returned telemetry states are explicitly labeled as 'simulated'.
10. Confirm physical hardware torque remained disabled throughout.
"""
import pytest
import numpy as np

from backend.cdpr.simulation import CDPRSimulation
from backend.cdpr.hardware.simulator_driver import SimulatorDriver
from backend.cdpr.hardware.driver_base import OperatingMode, MeasurementProvenance


def test_end_to_end_simulation_lifecycle():
    # 1. Load canonical robot configuration and instantiate simulation engine
    sim = CDPRSimulation("config/robot_config.yaml")
    assert sim.config.frame.width_m == 0.500
    assert sim.config.frame.height_m == 0.400
    assert sim.config.platform.width_m == 0.100
    assert sim.config.platform.height_m == 0.080

    # 2. Attach and start SimulatorDriver
    driver = SimulatorDriver(sim)
    driver_status = driver.get_status()
    assert driver_status["driver"] == "SimulatorDriver"
    assert driver_status["operating_mode"] == OperatingMode.SIMULATION.value
    assert driver_status["hardware_attached"] is False
    assert driver_status["homing_state"] == "HOMED"

    # 3. Submit valid target within workspace: target = [60 mm, 40 mm] = [0.060, 0.040] m
    target_q = np.array([0.060, 0.040])
    val_ok, val_msg = driver.validate_command(target_q, speed_m_s=0.08)
    assert val_ok is True

    # 4. Request movement
    move_ok, move_msg = driver.request_move(target_q, speed_m_s=0.08)
    assert move_ok is True
    assert sim.controller.mode == "MOVING"

    # 5. Deterministically step simulation loop until trajectory completes (target reached)
    max_steps = 400
    for _ in range(max_steps):
        sim.step()
        if sim.controller.mode == "IDLE":
            break

    assert sim.controller.mode == "IDLE"

    # 6. Read latest telemetry from driver
    state = driver.read_state()
    telem = sim.latest_telemetry
    assert telem is not None

    # 7. Check cable lengths
    expected_lengths = sim.geom.cable_lengths(target_q)
    np.testing.assert_allclose(state.cable_lengths, expected_lengths, atol=1e-4)

    # 8. Forward kinematics reconstruction and comparison with target
    assert telem.estimated_valid is True
    assert telem.tracking_error_valid is True
    assert telem.tracking_error_mm < 1.0  # Acceptable tolerance < 1 mm (0.001 m)

    # 9. Confirm provenance labels
    assert state.position_provenance == MeasurementProvenance.SIMULATED
    assert telem.position_provenance == "simulated"
    assert telem.operating_mode == "SIMULATION"

    # 10. Confirm hardware was never touched
    capabilities = driver.get_capabilities()
    assert capabilities["physical_torque_enabled"] is False
    assert capabilities["simulation_only"] is True
