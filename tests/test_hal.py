"""
Unit and integration tests for the Hardware Abstraction Layer (HAL).
Validates:
1. SimulatorDriver execution and simulated provenance tagging.
2. HardwareDriver unverified safety interlocks (Rule 0.2 and Rule 0.5).
3. Operating mode transitions (/api/mode) and rejection of unverified hardware motion.
4. Hardware status and profile reporting.
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app, sim
from backend.cdpr.hardware.driver_base import OperatingMode, MeasurementProvenance, HomingState
from backend.cdpr.hardware.simulator_driver import SimulatorDriver
from backend.cdpr.hardware.hardware_driver import HardwareDriver


@pytest.fixture
def client():
    return TestClient(app)


def test_simulator_driver_state_and_provenance():
    driver = SimulatorDriver(sim)
    assert driver.connect()[0] is True
    status = driver.get_status()
    assert status["operating_mode"] == OperatingMode.SIMULATION.value
    assert status["hardware_attached"] is False

    state = driver.read_state()
    assert state.position_provenance == MeasurementProvenance.SIMULATED
    assert state.operating_mode == OperatingMode.SIMULATION
    assert state.homing_state == HomingState.HOMED
    assert len(state.cable_lengths) == 4


def test_hardware_driver_unverified_safety_block():
    driver = HardwareDriver(sim.config)
    status = driver.get_status()
    assert status["hardware_ready"] is False
    assert status["hardware_motion_enabled"] is False
    assert len(status["missing_prerequisites"]) > 0

    # Connection fails when hardware profile is unverified
    ok, msg = driver.connect()
    assert ok is False
    assert "rejected" in msg.lower()

    # Move command must be strictly blocked
    target = np.array([0.05, 0.03])
    val_ok, val_msg = driver.validate_command(target)
    assert val_ok is False

    move_ok, move_msg = driver.request_move(target)
    assert move_ok is False
    assert "safety policy" in move_msg.lower() or "blocked" in move_msg.lower()


def test_mode_switching_via_api(client):
    # Ensure starting in SIMULATION
    res_sim = client.post("/api/mode", json={"mode": "SIMULATION"})
    assert res_sim.status_code == 200
    assert res_sim.json()["operating_mode"] == "SIMULATION"

    # Requesting HARDWARE mode with unverified hardware must result in rejected_unverified / HARDWARE_DISABLED
    res_hw = client.post("/api/mode", json={"mode": "HARDWARE"})
    assert res_hw.status_code == 200
    data_hw = res_hw.json()
    assert data_hw["status"] == "rejected_unverified"
    assert data_hw["operating_mode"] == "HARDWARE_DISABLED"
    assert "missing_prerequisites" in data_hw

    # Restore SIMULATION mode
    res_restore = client.post("/api/mode", json={"mode": "SIMULATION"})
    assert res_restore.status_code == 200
    assert res_restore.json()["operating_mode"] == "SIMULATION"


def test_hardware_status_endpoints(client):
    res_prof = client.get("/api/hardware/profile")
    assert res_prof.status_code == 200
    prof = res_prof.json()
    assert "driver" in prof
    assert prof["driver"] == "HardwareDriver"
    assert prof["hardware_ready"] is False

    res_stat = client.get("/api/hardware/status")
    assert res_stat.status_code == 200
    stat = res_stat.json()
    assert "missing_prerequisites" in stat
