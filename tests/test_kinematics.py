"""Unit tests for kinematics, analytical Jacobian vs finite-difference, and forward kinematics."""
import pytest
import numpy as np
from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics


@pytest.fixture
def kin():
    cfg = load_robot_config("robot_config.yaml")
    geom = Geometry(cfg)
    return Kinematics(geom)


def test_inverse_kinematics_positive_lengths(kin):
    """IK must return 4 positive lengths within workspace."""
    test_positions = [
        np.array([0.0, 0.0]),
        np.array([0.1, 0.05]),
        np.array([-0.08, -0.06]),
        np.array([0.15, -0.10])
    ]
    for q in test_positions:
        res = kin.inverse_kinematics(q)
        assert res.is_valid
        assert len(res.lengths) == 4
        assert np.all(res.lengths > 0.05)


def test_jacobian_analytical_vs_finite_difference(kin):
    """Verify analytical Jacobian matches central finite difference derivatives."""
    test_positions = [
        np.array([0.0, 0.0]),
        np.array([0.05, 0.03]),
        np.array([-0.07, 0.04]),
        np.array([0.10, -0.08])
    ]
    eps = 1e-6

    for q in test_positions:
        J_analytical = kin.jacobian(q)

        # Finite difference calculation
        J_fd = np.zeros((4, 2))
        for j in range(2):
            delta = np.zeros(2)
            delta[j] = eps
            L_plus = kin.geom.cable_lengths(q + delta)
            L_minus = kin.geom.cable_lengths(q - delta)
            J_fd[:, j] = (L_plus - L_minus) / (2.0 * eps)

        np.testing.assert_allclose(J_analytical, J_fd, rtol=1e-5, atol=1e-6)


def test_forward_kinematics_recovery(kin):
    """FK solver must recover true coordinates from computed cable lengths."""
    known_targets = [
        np.array([0.0, 0.0]),
        np.array([0.05, 0.04]),
        np.array([-0.06, -0.05]),
        np.array([0.12, -0.08])
    ]

    for q_true in known_targets:
        lengths = kin.geom.cable_lengths(q_true)
        # Give perturbed initial guess
        q_guess = q_true + np.random.uniform(-0.02, 0.02, size=2)
        res = kin.forward_kinematics(lengths, q_initial=q_guess)

        assert res.converged
        assert res.residual_norm < 1e-6
        np.testing.assert_allclose(res.q_estimated, q_true, atol=1e-5)


def test_forward_kinematics_incompatible_lengths(kin):
    """FK solver should reject physically incompatible cable lengths."""
    # Impossible lengths that cannot physically meet at any platform coordinate
    incompatible_lengths = np.array([0.1, 0.9, 0.1, 0.9])
    res = kin.forward_kinematics(incompatible_lengths)
    assert not res.converged or res.residual_norm > 0.05
