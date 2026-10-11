"""Unit tests for actuator kinematics, spooling calculations, speed/torque limits."""
import pytest
import numpy as np
from backend.cdpr.config import load_robot_config
from backend.cdpr.actuator import ActuatorArray


@pytest.fixture
def actuators():
    cfg = load_robot_config("robot_config.yaml")
    return ActuatorArray(cfg)


def test_rpm_calculation(actuators):
    """
    Verify RPM conversion:
    v = 0.100 m/s (100 mm/s)
    r = 0.010 m (10 mm)
    omega = 0.100 / 0.010 = 10 rad/s
    RPM = 10 * 60 / (2 * pi) ≈ 95.49296 RPM
    """
    v = np.array([0.100, -0.050, 0.0, 0.025])
    rpms = actuators.calculate_rpm(v)
    expected_rpm_0 = 10.0 * 60.0 / (2.0 * np.pi)
    assert pytest.approx(expected_rpm_0, rel=1e-4) == rpms[0]
    assert pytest.approx(-expected_rpm_0 / 2.0, rel=1e-4) == rpms[1]


def test_motor_speed_saturation_flag(actuators):
    """Speed exceeding 300 RPM must trigger speed saturation flag."""
    init_L = np.full(4, 0.25)
    actuators.reset(init_L)

    # 300 RPM corresponds to ~314 mm/s = 0.31416 m/s
    # Try 0.4 m/s (> 380 RPM)
    high_rates = np.array([0.4, 0.05, 0.05, 0.05])
    tensions = np.array([10.0, 10.0, 10.0, 10.0])

    states = actuators.update(init_L, high_rates, tensions)
    assert states[0].speed_saturated
    assert states[0].fault_code == "SPEED_LIMIT"
    # Channel 1 should be within limits
    assert not states[1].speed_saturated


def test_motor_torque_saturation_flag(actuators):
    """Torque exceeding 0.4 Nm limit must trigger torque saturation flag."""
    init_L = np.full(4, 0.25)
    actuators.reset(init_L)

    rates = np.zeros(4)
    # T = 50 N, r = 0.01m, eff = 0.90 -> tau = 50 * 0.01 / 0.90 = 0.555 Nm > 0.4 Nm
    high_tensions = np.array([50.0, 5.0, 5.0, 5.0])
    states = actuators.update(init_L, rates, high_tensions)

    assert states[0].torque_saturated
    assert states[0].fault_code == "TORQUE_LIMIT"
    assert not states[1].torque_saturated
