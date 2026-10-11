"""Unit tests for trajectory generation, path validation, and constraint enforcement."""
import pytest
import numpy as np
from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver
from backend.cdpr.collision import CollisionChecker
from backend.cdpr.trajectory import TrajectoryPlanner


@pytest.fixture
def planner():
    cfg = load_robot_config("robot_config.yaml")
    geom = Geometry(cfg)
    kin = Kinematics(geom)
    ts = TensionSolver(kin)
    col = CollisionChecker(geom)
    return TrajectoryPlanner(cfg, kin, ts, col)


def test_point_to_point_reaches_target(planner):
    """Straight line path must start at q_start and end precisely at q_goal within velocity limits."""
    q_start = np.array([0.0, 0.0])
    q_goal = np.array([0.10, 0.05])

    points = planner.plan_point_to_point(q_start, q_goal, v_target=0.08)
    assert len(points) > 10
    np.testing.assert_allclose(points[0].q, q_start, atol=1e-5)
    np.testing.assert_allclose(points[-1].q, q_goal, atol=1e-5)

    # Check nominal speed limit 100 mm/s
    for p in points:
        speed = np.linalg.norm(p.q_dot)
        assert speed <= planner.v_max_nominal + 1e-4


def test_trajectory_validation_feasible_path(planner):
    """A modest point-to-point move within interior workspace must pass all feasibility checks."""
    q_start = np.array([0.0, 0.0])
    q_goal = np.array([0.08, 0.06])
    points = planner.plan_point_to_point(q_start, q_goal, v_target=0.05)

    val = planner.validate_trajectory(points)
    assert val.is_feasible
    assert val.violation_code == "OK"
    assert val.max_cable_rpm < 300.0


def test_trajectory_validation_boundary_rejection(planner):
    """A trajectory reaching outside the frame boundaries must be detected and rejected."""
    q_start = np.array([0.0, 0.0])
    # Target outside allowed workspace (frame half-width is 0.25, platform half-width 0.05 -> bound 0.18m)
    q_out = np.array([0.22, 0.0])
    points = planner.plan_point_to_point(q_start, q_out, v_target=0.05)

    val = planner.validate_trajectory(points)
    assert not val.is_feasible
    assert val.violation_code == "WORKSPACE_LIMIT"
