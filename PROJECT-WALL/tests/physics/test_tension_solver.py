import pytest
import numpy as np

from app.kinematics.cdpr_kinematics import CDPRKinematics, AnchorPoint, PlatformGeometry
from app.dynamics.tension_solver import CableTensionSolver, TensionLimits


@pytest.fixture
def solver():
    anchors = {
        "A1": AnchorPoint("A1", 0.0, 600.0),
        "A2": AnchorPoint("A2", 800.0, 600.0),
        "A3": AnchorPoint("A3", 0.0, 0.0),
        "A4": AnchorPoint("A4", 800.0, 0.0),
    }
    platform = PlatformGeometry(width_mm=100.0, height_mm=80.0, thickness_mm=6.0, mass_kg=0.5)
    kin = CDPRKinematics(anchors=anchors, platform=platform)
    return CableTensionSolver(kin, limits=TensionLimits(min_tension_n=2.0, max_tension_n=50.0))


def test_tension_at_nominal_center(solver):
    res = solver.solve_static_tensions(400.0, 300.0)
    assert res.is_feasible
    assert res.equilibrium_residual_n < 0.1

    # All 4 tensions must be positive and within bounds [2.0, 50.0]
    for t in res.tensions_n:
        assert 2.0 <= t <= 50.0

    # Since gravity acts downwards (-Y), upper cables (C1, C2) must pull to support weight
    assert res.tensions_n[0] >= 2.0
    assert res.tensions_n[1] >= 2.0


def test_tension_feasibility_across_printable_workspace(solver):
    # Test points inside safe region
    points = [
        (200.0, 200.0),
        (600.0, 200.0),
        (200.0, 400.0),
        (600.0, 400.0),
        (400.0, 300.0)
    ]
    for x, y in points:
        res = solver.solve_static_tensions(x, y)
        assert res.is_feasible
        assert res.equilibrium_residual_n < 0.15
