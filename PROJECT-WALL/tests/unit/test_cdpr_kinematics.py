import pytest
import numpy as np
import math

from app.kinematics.cdpr_kinematics import CDPRKinematics, AnchorPoint, PlatformGeometry


@pytest.fixture
def cdpr():
    anchors = {
        "A1": AnchorPoint("A1", 0.0, 600.0),
        "A2": AnchorPoint("A2", 800.0, 600.0),
        "A3": AnchorPoint("A3", 0.0, 0.0),
        "A4": AnchorPoint("A4", 800.0, 0.0),
    }
    platform = PlatformGeometry(width_mm=100.0, height_mm=80.0, thickness_mm=6.0, mass_kg=0.5)
    return CDPRKinematics(anchors=anchors, platform=platform)


def test_inverse_kinematics_center(cdpr):
    # At center (400, 300)
    lengths = cdpr.inverse_kinematics(400.0, 300.0)
    assert len(lengths) == 4
    for l in lengths:
        assert l > 0.0
        # Cable lengths to center should be around 430 - 450 mm
        assert 400.0 < l < 500.0


def test_forward_kinematics_roundtrip(cdpr):
    test_points = [(400.0, 300.0), (350.0, 250.0), (450.0, 350.0), (200.0, 200.0)]
    for tx, ty in test_points:
        lens = cdpr.inverse_kinematics(tx, ty)
        ok, est_x, est_y, res = cdpr.forward_kinematics(lens, initial_guess=(tx + 10.0, ty - 10.0))
        assert ok
        assert math.isclose(est_x, tx, abs_tol=0.05)
        assert math.isclose(est_y, ty, abs_tol=0.05)
        assert res < 0.1


def test_jacobian_structure_and_conditioning(cdpr):
    J = cdpr.jacobian_matrix(400.0, 300.0)
    assert J.shape == (4, 2)
    # Norm of each unit direction row should be 1.0
    for i in range(4):
        norm = np.linalg.norm(J[i, :])
        assert math.isclose(norm, 1.0, abs_tol=1e-4)

    # Conditioning index at center should be healthy (> 0.4)
    cond = cdpr.kinematic_conditioning_index(400.0, 300.0)
    assert cond > 0.4

