"""Tests for flat-scene degeneracy guard (Acceptance check 3)."""

import numpy as np
from depthwizard.calibration.ransac_affine import calibrate_path_c


def test_flat_water_triggers_degeneracy_guard_without_nan() -> None:
    """Acceptance check 3: Flat water input triggers flat-scene guard without NaN/Inf."""
    H, W = 100, 100
    # Flat water body with zero variance
    flat_water_disp = np.full((H, W), 0.15, dtype=np.float32)

    calibrated_dsm, meta = calibrate_path_c(flat_water_disp)

    # Must trigger degeneracy guard
    assert meta["is_degenerate"] is True
    assert meta["flat_scene"] is True

    # Must contain NO NaN or Inf
    assert np.all(np.isfinite(calibrated_dsm)), "Output contains NaN or Inf values!"
    assert not np.isnan(calibrated_dsm).any()
    assert not np.isinf(calibrated_dsm).any()


def test_desert_near_zero_variance_triggers_guard() -> None:
    """Featureless desert or salt flat with variance < 1e-4 triggers guard."""
    H, W = 100, 100
    np.random.seed(42)
    # Variance is 1e-6 (far below 1e-4 threshold)
    desert_disp = (0.20 + np.random.normal(0, 0.001, (H, W))).astype(np.float32)
    assert np.var(desert_disp) < 1e-4

    ref_dem = np.full((H, W), 450.0, dtype=np.float32)

    calibrated_dsm, meta = calibrate_path_c(desert_disp, reference_dem=ref_dem)

    assert meta["is_degenerate"] is True
    assert meta["flat_scene"] is True
    assert np.all(np.isfinite(calibrated_dsm))
    # Should maintain reference terrain level without exploding
    assert np.allclose(calibrated_dsm, 450.0)


def test_empty_or_all_nan_disparity_guarded() -> None:
    """Completely invalid / NaN input array is handled gracefully."""
    H, W = 50, 50
    nan_disp = np.full((H, W), np.nan, dtype=np.float32)

    calibrated_dsm, meta = calibrate_path_c(nan_disp)

    assert meta["is_degenerate"] is True
    assert np.all(np.isfinite(calibrated_dsm))


def test_low_elevation_variance_reference_triggers_degenerate_flat_terrain() -> None:
    """Reference DEM with elevation standard deviation < 5.0m triggers DEGENERATE_FLAT_TERRAIN."""
    H, W = 100, 100
    np.random.seed(42)
    # Deliberately flat reference DEM: elevation std = 1.8m (< 5.0m threshold)
    flat_ref = (120.0 + np.random.normal(0, 1.8, (H, W))).astype(np.float32)
    assert np.std(flat_ref) < 5.0

    disparity = np.random.uniform(0.15, 0.35, (H, W)).astype(np.float32)

    calibrated_dsm, meta = calibrate_path_c(
        disparity,
        reference_dem=flat_ref,
        assumed_max_structure_height_m=35.0,
    )

    assert meta["calibration_status"] == "DEGENERATE_FLAT_TERRAIN"
    assert meta["status"] == "DEGENERATE_FLAT_TERRAIN"
    assert meta["is_degenerate"] is True
    assert meta["flat_scene"] is True
    assert "inlier_fraction" in meta
    assert "a" in meta and "b" in meta

    # Height variation above ground must stay within [0, 1.5 * assumed_max_structure_height_m]
    height_range = float(np.ptp(calibrated_dsm))
    assert height_range <= 1.5 * 35.0
    assert np.all(np.isfinite(calibrated_dsm))
