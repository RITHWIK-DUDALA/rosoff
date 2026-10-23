"""
Unit tests for State Estimator (FK reconstruction, tracking error, staleness).
"""
import pytest
import numpy as np

from backend.cdpr.config import load_robot_config
from backend.cdpr.geometry import Geometry
from backend.cdpr.kinematics import Kinematics
from backend.cdpr.state_estimation.estimator import StateEstimator, StateEstimateResult
from backend.cdpr.hardware.driver_base import MeasurementProvenance


@pytest.fixture
def estimator():
    cfg = load_robot_config("config/robot_config.yaml")
    geom = Geometry(cfg)
    kin = Kinematics(geom)
    return StateEstimator(kin, stale_timeout_s=0.5)


def test_accurate_state_estimation_from_cable_lengths(estimator):
    # Known platform position [60 mm, -40 mm] = [0.06, -0.04] m
    q_true = np.array([0.06, -0.04])
    lengths = estimator.kin.geom.cable_lengths(q_true)

    res: StateEstimateResult = estimator.estimate_state(
        measured_lengths=lengths,
        commanded_q=q_true,
        measurement_timestamp=10.0,
        provenance=MeasurementProvenance.SIMULATED
    )

    assert res.is_valid is True
    assert res.tracking_error_valid is True
    assert res.residual_norm < 1e-6
    assert res.tracking_error_m < 1e-5
    np.testing.assert_allclose(res.q_estimated, q_true, atol=1e-5)
    assert res.provenance == MeasurementProvenance.SIMULATED


def test_divergent_lengths_handling(estimator):
    # Geometrically incompatible lengths
    bad_lengths = np.array([0.05, 0.90, 0.05, 0.90])
    res = estimator.estimate_state(
        measured_lengths=bad_lengths,
        commanded_q=np.array([0.0, 0.0]),
        measurement_timestamp=12.0
    )

    assert res.is_valid is False
    assert res.tracking_error_valid is False
    assert np.isnan(res.tracking_error_m) or res.tracking_error_m > 0.05


def test_stale_feedback_detection(estimator):
    q_true = np.array([0.0, 0.0])
    lengths = estimator.kin.geom.cable_lengths(q_true)

    # Initial update at t = 1.0s
    res1 = estimator.estimate_state(lengths, q_true, measurement_timestamp=1.0)
    assert res1.is_stale is False

    # Second update after timeout (t = 2.0s, delta = 1.0s > 0.5s timeout)
    res2 = estimator.estimate_state(lengths, q_true, measurement_timestamp=2.0)
    assert res2.is_stale is True
    assert res2.tracking_error_valid is False
    assert "STALE" in res2.status_message
