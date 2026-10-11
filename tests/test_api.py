"""Integration tests for FastAPI REST endpoints and configuration retrieval."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app, sim


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "sim_time_s" in data
    assert "mode" in data


def test_config_endpoint(client):
    res = client.get("/api/config")
    assert res.status_code == 200
    cfg = res.json()
    assert "frame" in cfg
    assert "platform" in cfg
    assert "cables" in cfg
    assert "actuators" in cfg


def test_workspace_endpoint(client):
    res = client.get("/api/workspace")
    assert res.status_code == 200
    ws = res.json()
    assert ws["frame_width_mm"] == 300.0
    assert ws["frame_height_mm"] == 200.0
    assert ws["platform_width_mm"] == 60.0
    assert ws["platform_height_mm"] == 40.0
    assert "anchors_mm" in ws


def test_move_command_validation(client):
    # Valid move command
    res = client.post("/api/command/move", json={"x_mm": 50, "y_mm": 30, "speed_mm_s": 80})
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"

    # Out of workspace move command must return 400
    res_bad = client.post("/api/command/move", json={"x_mm": 220, "y_mm": 0})
    assert res_bad.status_code == 400
    assert res_bad.json()["detail"]["error"] == "MoveRejected"


def test_pause_resume_stop_endpoints(client):
    # Stop command
    res = client.post("/api/command/stop")
    assert res.status_code == 200

    # Reset command
    res_reset = client.post("/api/command/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "reset"
