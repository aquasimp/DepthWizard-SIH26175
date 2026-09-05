"""Tests for Path C: Disparity RANSAC affine alignment."""

import numpy as np
import pytest
from depthwizard.calibration.ransac_affine import calibrate_path_c


def test_ransac_fits_reference_with_outliers() -> None:
    """RANSAC recovers true affine scale and shift despite 25% outlier noise."""
    H, W = 100, 100
    y, x = np.mgrid[0:H, 0:W]
    # Clean relationship: z = 20.0 * d + 50.0
    true_s = 20.0
    true_t = 50.0

    np.random.seed(42)
    disparity = np.random.uniform(0.1, 0.4, (H, W)).astype(np.float32)
    ref_dem = (true_s * disparity + true_t).astype(np.float32)

    # Corrupt 25% of reference DEM with extreme outliers (e.g. cloud/shadow artifacts)
    outlier_mask = np.random.rand(H, W) < 0.25
    ref_dem[outlier_mask] += np.random.uniform(-50.0, 50.0, size=np.sum(outlier_mask)).astype(
        np.float32
    )

    calibrated_dsm, meta = calibrate_path_c(disparity, reference_dem=ref_dem)

    assert meta["calibration_path"] == "PATH_C_RANSAC_AFFINE"
    assert meta["status"] == "CALIBRATED"
    assert meta["is_degenerate"] is False

    # Scale and shift should be close to true values (within 15%)
    assert pytest.approx(meta["scale"], rel=0.15) == true_s
    assert pytest.approx(meta["shift"], rel=0.15) == true_t


def test_ransac_building_prior_without_reference() -> None:
    """Without reference DEM, Path C uses building prior to produce metric heights."""
    H, W = 100, 100
    np.random.seed(42)
    # Typical relative disparity range [0.15, 0.35]
    disparity = np.random.uniform(0.15, 0.35, (H, W)).astype(np.float32)

    calibrated_dsm, meta = calibrate_path_c(
        disparity, reference_dem=None, typical_structure_height_m=12.0
    )

    assert meta["calibration_path"] == "PATH_C_RANSAC_AFFINE"
    assert meta["status"] == "CALIBRATED"
    assert meta["scale"] > 0.0

    # 95th percentile minus 5th percentile should be close to 12.0m prior
    p5 = float(np.percentile(calibrated_dsm, 5))
    p95 = float(np.percentile(calibrated_dsm, 95))
    assert pytest.approx(p95 - p5, rel=0.1) == 12.0
