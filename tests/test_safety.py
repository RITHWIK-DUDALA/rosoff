"""
Unit tests for SafetyManager, limit protections, and E-STOP latching.
"""
import pytest
import numpy as np

from backend.cdpr.config import load_robot_config
from backend.cdpr.safety.safety_manager import SafetyManager, FaultSeverity


@pytest.fixture
def safety():
    cfg = load_robot_config("config/robot_config.yaml")
    return SafetyManager(cfg)


def test_workspace_boundary_protection(safety):
    # Within bounds (canonical bounds: [-0.180, +0.180], [-0.140, +0.140])
    ok_in, _ = safety.check_workspace(np.array([0.100, 0.050]))
    assert ok_in is True

    # Outside bounds
    ok_out, rec = safety.check_workspace(np.array([0.220, 0.0]))
    assert ok_out is False
    assert rec.code == "OUT_OF_WORKSPACE"


def test_motor_speed_protection(safety):
    # Safe RPM (< 300 RPM)
    ok_safe, _ = safety.check_speed(np.array([100.0, 150.0, -120.0, 50.0]))
    assert ok_safe is True

    # Over speed limit (> 300 RPM)
    ok_over, rec = safety.check_speed(np.array([350.0, 50.0, 50.0, 50.0]))
    assert ok_over is False
    assert rec.code == "SPEED_LIMIT_EXCEEDED"


def test_motor_torque_protection(safety):
    # Safe torque (<= 0.40 Nm)
    ok_safe, _ = safety.check_torques(np.array([0.25, 0.30, 0.15, 0.20]))
    assert ok_safe is True

    # Exceeding 0.4 Nm
    ok_over, rec = safety.check_torques(np.array([0.55, 0.10, 0.10, 0.10]))
    assert ok_over is False
    assert rec.code == "TORQUE_LIMIT_EXCEEDED"


def test_estop_latching_and_reset_policy(safety):
    assert safety.is_estop_active is False
    safety.trigger_estop("Test emergency button pressed")
    assert safety.is_estop_active is True
    assert "EMERGENCY_STOP_ACTIVE" in safety.active_fault_codes

    # Hardware mode reset must be blocked
    ok_hw_reset, _ = safety.reset_faults(is_hardware_mode=True)
    assert ok_hw_reset is False

    # Simulation reset can clear software fault
    ok_sim_reset, _ = safety.reset_faults(is_hardware_mode=False)
    assert ok_sim_reset is True
    assert safety.is_estop_active is False
