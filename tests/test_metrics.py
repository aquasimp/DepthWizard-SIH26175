"""Unit tests for elevation error metrics, LE90, NMAD, and histograms."""

import numpy as np
import pytest

from depthwizard.eval.metrics import compute_elevation_metrics, compute_error_histogram


def test_metrics_constant_bias():
    """Verify exact analytic metrics under pure uniform bias."""
    ref = np.full((100, 100), 50.0, dtype=np.float32)
    pred = ref + 2.5  # Constant +2.5m bias

    metrics = compute_elevation_metrics(pred, ref)

    assert pytest.approx(metrics["bias"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["mae"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["rmse"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["medae"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["rmse_db"], abs=1e-3) == 0.0
    assert pytest.approx(metrics["std_error"], abs=1e-3) == 0.0
    assert pytest.approx(metrics["le90"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["le95"], abs=1e-3) == 2.5
    assert pytest.approx(metrics["nmad"], abs=1e-3) == 0.0
    assert pytest.approx(metrics["delta1"], abs=1e-3) == 0.0
    assert pytest.approx(metrics["delta2_5"], abs=1e-3) == 0.0
    assert metrics["valid_pixels"] == 10000


def test_metrics_perfect_prediction():
    """Verify zero error on perfect identity surfaces."""
    ref = np.linspace(10.0, 100.0, 1000, dtype=np.float32).reshape(25, 40)
    pred = ref.copy()

    metrics = compute_elevation_metrics(pred, ref)

    assert metrics["bias"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["le90"] == 0.0
    assert metrics["nmad"] == 0.0
    assert pytest.approx(metrics["pearson_r"], abs=1e-3) == 1.0
    assert metrics["delta1"] == 1.0
    assert metrics["delta2_5"] == 1.0


def test_metrics_nmad_resilience_to_outliers():
    """Verify that NMAD is resistant to extreme gross blunders/outliers whereas RMSE inflates."""
    np.random.seed(42)
    # 98% clean Gaussian noise with std=0.5m
    inliers = np.random.normal(0.0, 0.5, size=10000).astype(np.float32)
    # 2% gross blunders with +50m error
    inliers[:200] = 50.0

    ref = np.zeros(10000, dtype=np.float32)
    pred = inliers

    metrics = compute_elevation_metrics(pred, ref)

    # RMSE should be heavily pulled by the +50m blunders (> 7m)
    assert metrics["rmse"] > 7.0
    # NMAD should remain close to the true standard deviation of the inliers (~0.5m)
    assert metrics["nmad"] < 1.0
    assert metrics["nmad"] < metrics["rmse"]


def test_metrics_mask_and_nodata():
    """Verify that -9999.0 and NaNs are excluded from evaluation."""
    ref = np.array([[10.0, 20.0], [30.0, -9999.0]], dtype=np.float32)
    pred = np.array([[12.0, np.nan], [31.0, 40.0]], dtype=np.float32)

    metrics = compute_elevation_metrics(pred, ref)

    # Only (0,0) with diff=2.0 and (1,0) with diff=1.0 are valid
    assert metrics["valid_pixels"] == 2
    assert pytest.approx(metrics["bias"], abs=1e-3) == 1.5
    assert pytest.approx(metrics["mae"], abs=1e-3) == 1.5


def test_error_histogram_bins():
    """Verify histogram counts and edge distributions."""
    diff = np.array([-10.0, -5.0, 0.0, 2.5, 5.0, 10.0], dtype=np.float32)
    hist = compute_error_histogram(diff, num_bins=10, range_m=(-15.0, 15.0))

    assert len(hist["counts"]) == 10
    assert len(hist["bin_edges"]) == 11
    assert len(hist["bin_centers"]) == 10
    assert sum(hist["counts"]) == len(diff)
