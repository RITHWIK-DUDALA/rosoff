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
    # C1: (-0.25,  0.20)
    # C2: ( 0.25,  0.20)
    # C3: ( 0.25, -0.20)
    # C4: (-0.25, -0.20)
    expected = np.array([
        [-0.25,  0.20],
        [ 0.25,  0.20],
        [ 0.25, -0.20],
        [-0.25, -0.20]
    ])
    np.testing.assert_allclose(robot.anchors, expected, atol=1e-6)


def test_platform_attachments(robot):
    """Verify local platform attachment positions."""
    expected = np.array([
        [-0.05,  0.04],
        [ 0.05,  0.04],
        [ 0.05, -0.04],
        [-0.05, -0.04]
    ])
    np.testing.assert_allclose(robot.attachments, expected, atol=1e-6)


def test_home_cable_lengths_and_symmetry(robot):
    """Verify all four cable lengths at center home position [0, 0] are identical and correct."""
    q_home = np.array([0.0, 0.0])
    lengths = robot.cable_lengths(q_home)
    # At home: dx = 0.25 - 0.05 = 0.20 m, dy = 0.20 - 0.04 = 0.16 m
    # L = sqrt(0.20^2 + 0.16^2) = sqrt(0.04 + 0.0256) = sqrt(0.0656) ≈ 0.256124969 m
    expected_L = np.sqrt(0.20**2 + 0.16**2)
    assert len(lengths) == 4
    for l in lengths:
        assert pytest.approx(expected_L, abs=1e-5) == l

    # Test perfect symmetry
    assert np.allclose(lengths, lengths[0], atol=1e-6)


def test_known_coordinates_lengths(robot):
    """Verify cable lengths at non-symmetric coordinate [0.05, -0.02] m."""
    q = np.array([0.05, -0.02])
    lengths = robot.cable_lengths(q)
    # C1: P1 = [0, 0.02], A1 = [-0.25, 0.20] -> dx = -0.25, dy = 0.18 -> L1 = sqrt(0.25^2 + 0.18^2)
    l1_exp = np.hypot(-0.25, 0.18)
    assert pytest.approx(l1_exp, abs=1e-5) == lengths[0]
