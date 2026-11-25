import pytest
from app.simulation.cdpr_orchestrator import CDPROrchestrator
from app.scenarios.scenario_manager import CDPRScenarioManager


@pytest.fixture
def orchestrator():
    return CDPROrchestrator()


def test_scenario_01_nominal_print(orchestrator):
    res = orchestrator.scenario_mgr.execute_scenario("scenario_01")
    assert res["status"] in ("SUCCESS", "EXECUTED")
    eval_res = res.get("evaluation", {})
    assert eval_res.get("passed") is True


def test_scenario_03_slack_detection(orchestrator):
    res = orchestrator.scenario_mgr.execute_scenario("scenario_03")
    eval_res = res.get("evaluation", {})
    assert eval_res.get("passed") is True
    assert "Slack" in eval_res.get("summary", "")


def test_scenario_04_overload_detection(orchestrator):
    res = orchestrator.scenario_mgr.execute_scenario("scenario_04")
    eval_res = res.get("evaluation", {})
    assert eval_res.get("passed") is True
    assert "Overload" in eval_res.get("summary", "")


def test_scenario_05_emergency_stop(orchestrator):
    res = orchestrator.scenario_mgr.execute_scenario("scenario_05")
    eval_res = res.get("evaluation", {})
    assert eval_res.get("passed") is True
    assert "EMERGENCY_STOP" in eval_res.get("summary", "")


def test_scenario_09_actuator_swap(orchestrator):
    res = orchestrator.scenario_mgr.execute_scenario("scenario_09")
    eval_res = res.get("evaluation", {})
    assert eval_res.get("passed") is True

