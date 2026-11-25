import pytest

from app.cables.cable_system import FourCableSystem
from app.safety.supervisory_state_machine import CDPRSupervisor, CDPRSystemState, FaultSeverity


def test_slack_cable_detection():
    cables = FourCableSystem([500.0, 500.0, 500.0, 500.0])
    # Tensions: C1 has only 1.0 N (< 2.0 N min threshold)
    cables.update_all([500.0, 500.0, 500.0, 500.0], [1.0, 15.0, 15.0, 15.0])

    has_fault, msg = cables.has_any_fault()
    assert has_fault
    assert "slack" in msg.lower()
    assert cables.cables["C1"].is_slack


def test_overload_cable_detection():
    cables = FourCableSystem([500.0, 500.0, 500.0, 500.0])
    # Tensions: C4 has 70.0 N (> 65.0 N max threshold)
    cables.update_all([500.0, 500.0, 500.0, 500.0], [12.0, 12.0, 12.0, 70.0])

    has_fault, msg = cables.has_any_fault()
    assert has_fault
    assert "overload" in msg.lower()
    assert cables.cables["C4"].is_overloaded


def test_supervisor_state_transitions():
    sup = CDPRSupervisor()
    assert sup.state == CDPRSystemState.READY

    # Valid transitions
    assert sup.transition_to(CDPRSystemState.PRINTING, "Print job started")
    assert sup.transition_to(CDPRSystemState.PAUSED, "Operator paused")
    assert sup.transition_to(CDPRSystemState.PRINTING, "Operator resumed")

    # Fault transition to E-Stop
    sup.report_fault("TEST_FLT", "Simulated cable break", "CABLES", FaultSeverity.EMERGENCY_SHUTDOWN)
    assert sup.state == CDPRSystemState.EMERGENCY_STOP

    # Reset
    sup.reset()
    assert sup.state == CDPRSystemState.READY
