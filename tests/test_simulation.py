"""Integration tests for deterministic simulation loop and telemetry."""
import pytest
import numpy as np
from backend.cdpr.simulation import CDPRSimulation


@pytest.fixture
def sim():
    return CDPRSimulation("robot_config.yaml")


def test_initial_telemetry_state(sim):
    """Initial state at origin must be valid, idle, and symmetric."""
    telem = sim.latest_telemetry
    assert telem is not None
    assert telem.controller_mode == "IDLE"
    assert pytest.approx(0.0, abs=1e-3) == telem.platform_x_mm
    assert pytest.approx(0.0, abs=1e-3) == telem.platform_y_mm
    assert telem.workspace_safe
    assert telem.tension_feasible
    assert len(telem.cable_lengths_mm) == 4
    # All 4 lengths identical at center
    assert pytest.approx(telem.cable_lengths_mm[0], abs=1e-2) == telem.cable_lengths_mm[1]


def test_move_command_and_simulation_stepping(sim):
    """Issuing a move command advances the simulation deterministically to the target."""
    ok, msg = sim.controller.request_move(np.array([0.05, 0.03]), speed_m_s=0.08)
    assert ok
    assert sim.controller.mode == "MOVING"

    # Step simulation until motion completes or max steps
    max_steps = 300
    for _ in range(max_steps):
        sim.step()
        if sim.controller.mode == "IDLE":
            break

    assert sim.controller.mode == "IDLE"
    # Verify final pose matches target [50, 30] mm
    assert pytest.approx(50.0, abs=1.0) == sim.latest_telemetry.platform_x_mm
    assert pytest.approx(30.0, abs=1.0) == sim.latest_telemetry.platform_y_mm


def test_estop_and_reset(sim):
    """Emergency stop stops motion and locks state until reset."""
    sim.controller.request_move(np.array([0.08, 0.05]))
    sim.step()

    # Trigger E-STOP
    ok, msg = sim.controller.estop()
    assert ok
    assert sim.controller.mode == "ESTOP"
    assert "EMERGENCY_STOP_ACTIVE" in sim.controller.active_faults

    # Cannot move during ESTOP
    ok2, _ = sim.controller.request_move(np.array([0.0, 0.0]))
    assert not ok2

    # Reset recovers system
    ok_res, _ = sim.controller.reset()
    assert ok_res
    assert sim.controller.mode == "IDLE"
    assert len(sim.controller.active_faults) == 0
