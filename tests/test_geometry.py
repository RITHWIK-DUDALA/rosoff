"""Unit tests for robot geometry and coordinate conventions."""
import pytest
import numpy as np
from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry


@pytest.fixture
def robot():
    cfg = load_robot_config("robot_config.yaml")
    return Geometry(cfg)


def test_anchor_positions(robot):
    """Verify the four configured anchor positions in meters."""
    # C1: (-0.15,  0.10)
    # C2: ( 0.15,  0.10)
    # C3: ( 0.15, -0.10)
    # C4: (-0.15, -0.10)
    expected = np.array([
        [-0.15,  0.10],
        [ 0.15,  0.10],
        [ 0.15, -0.10],
        [-0.15, -0.10]
    ])
    np.testing.assert_allclose(robot.anchors, expected, atol=1e-6)


def test_platform_attachments(robot):
    """Verify local platform attachment positions."""
    expected = np.array([
        [-0.03,  0.02],
        [ 0.03,  0.02],
        [ 0.03, -0.02],
        [-0.03, -0.02]
    ])
    np.testing.assert_allclose(robot.attachments, expected, atol=1e-6)


def test_home_cable_lengths_and_symmetry(robot):
    """Verify all four cable lengths at center home position [0, 0] are identical and correct."""
    q_home = np.array([0.0, 0.0])
    lengths = robot.cable_lengths(q_home)
    # At home: dx = 0.15 - 0.03 = 0.12 m, dy = 0.10 - 0.02 = 0.08 m
    # L = sqrt(0.12^2 + 0.08^2) = sqrt(0.0144 + 0.0064) = sqrt(0.0208) ≈ 0.144222 m
    expected_L = np.sqrt(0.12**2 + 0.08**2)
    assert len(lengths) == 4
    for l in lengths:
        assert pytest.approx(expected_L, abs=1e-5) == l

    # Test perfect symmetry
    assert np.allclose(lengths, lengths[0], atol=1e-6)


def test_known_coordinates_lengths(robot):
    """Verify cable lengths at non-symmetric coordinate [0.03, -0.01] m."""
    q = np.array([0.03, -0.01])
    lengths = robot.cable_lengths(q)
    # C1: P1 = [0, 0.01], A1 = [-0.15, 0.10] -> dx = -0.15, dy = 0.09 -> L1 = sqrt(0.15^2 + 0.09^2)
    l1_exp = np.hypot(-0.15, 0.09)
    assert pytest.approx(l1_exp, abs=1e-5) == lengths[0]
