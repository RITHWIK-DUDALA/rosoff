import pytest
import math

from app.cables.cable_system import FourCableSystem, Cable
from app.motors.winch_motor import WinchMotor, DrumGeometry, MotorSpecifications, MotorStatus


def test_dyneema_elastic_elongation():
    cable = Cable("C1", "M1", "B1", initial_length_mm=1000.0)
    # At 0N tension, stretch is 0
    cable.update_state(1000.0, tension_n=0.0)
    assert cable.elastic_stretch_mm == 0.0

    # At 25N tension, stretch = (F * L) / (E * A)
    cable.update_state(1000.0, tension_n=25.0)
    ea = cable.props.elastic_modulus_mpa * cable.props.cross_section_area_mm2
    expected_stretch = (25.0 * 1000.0) / ea
    assert math.isclose(cable.elastic_stretch_mm, expected_stretch, abs_tol=1e-3)
    assert cable.current_length_mm == 1000.0 + cable.elastic_stretch_mm


def test_winch_drum_multilayer_tracking():
    motor = WinchMotor("M1", "Winch 1")
    initial_radius = motor.drum.core_radius_mm
    assert initial_radius == 10.0

    # Command winding delta of 200 mm
    dt = 0.033
    delta = motor.step(200.0, dt, cable_tension_n=15.0)
    assert delta > 0.0
    assert motor.encoder_ticks > 0
    assert motor.temperature_c >= 25.0


def test_motor_thermal_load_and_torque():
    motor = WinchMotor("M1", "Winch 1")
    # Apply continuous load
    for _ in range(100):
        motor.step(10.0, dt=0.033, cable_tension_n=30.0)

    # Temperature should have increased slightly due to electrical loss
    assert motor.temperature_c > 25.0
    assert motor.torque_nm > 0.0
