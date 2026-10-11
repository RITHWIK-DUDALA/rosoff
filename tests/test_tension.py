"""Unit tests for cable tension allocation and static force equilibrium."""
import pytest
import numpy as np
from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.tension_solver import TensionSolver


@pytest.fixture
def solver():
    cfg = load_robot_config("robot_config.yaml")
    geom = Geometry(cfg)
    kin = Kinematics(geom)
    return TensionSolver(kin)


def test_zero_wrench_equilibrium_at_origin(solver):
    """At origin under zero external wrench, all 4 tensions must be positive and equal due to symmetry."""
    q_home = np.array([0.0, 0.0])
    res = solver.solve(q_home)

    assert res.is_feasible
    assert res.status_code == "FEASIBLE"
    assert len(res.tensions) == 4
    # All tensions >= T_min
    assert np.all(res.tensions >= solver.t_min)
    # Tensions must not exceed max limit
    assert np.all(res.tensions <= solver.t_max)
    # Residual force must be within tolerance
    assert res.residual_norm < 0.01

    # Symmetry check: all 4 tensions should be identical
    np.testing.assert_allclose(res.tensions, res.tensions[0], rtol=1e-3)


def test_positive_tensions_with_lateral_force(solver):
    """Under lateral force, tensions must reallocate without violating nonnegativity."""
    q = np.array([0.05, -0.03])
    F_ext = np.array([5.0, -3.0]) # 5N in +X, -3N in Y
    res = solver.solve(q, F_ext=F_ext)

    assert res.is_feasible
    assert np.all(res.tensions >= solver.t_min)
    assert np.all(res.tensions <= solver.t_max)
    assert res.residual_norm < 0.01


def test_infeasible_extreme_force_rejected(solver):
    """An impossible external force (e.g. 1000 N) exceeding motor limits must be rejected as infeasible."""
    q = np.array([0.0, 0.0])
    F_extreme = np.array([1000.0, 0.0])
    res = solver.solve(q, F_ext=F_extreme)

    assert not res.is_feasible
    assert res.status_code == "INFEASIBLE_TENSION"
