"""Tests for Path A: SRTM DTM decomposition and absolute DSM generation."""

import numpy as np
from depthwizard.calibration.dtm_decompose import (
    calibrate_path_a,
    decompose_bare_earth_dtm,
)


def create_synthetic_hill_and_buildings(
    shape: tuple = (100, 100),
    hill_base_m: float = 100.0,
    hill_peak_m: float = 15.0,
) -> tuple:
    """Generate synthetic ground truth terrain and buildings."""
    H, W = shape
    y, x = np.mgrid[0:H, 0:W]

    # 1. Known hill: smooth 2D Gaussian with realistic topographic scale
    hill_dtm = hill_base_m + hill_peak_m * np.exp(-((x - 50) ** 2 + (y - 50) ** 2) / (2 * 80**2))
    hill_dtm = hill_dtm.astype(np.float32)

    # 2. Known buildings
    bldgs = np.zeros((H, W), dtype=np.float32)
    bldgs[20:30, 20:30] = 15.0  # Building 1: 15m (10x10 px footprint)
    bldgs[60:70, 20:30] = 25.0  # Building 2: 25m (10x10 px footprint)
    bldgs[25:35, 65:75] = 18.0  # Building 3: 18m (10x10 px footprint)

    true_dsm = (hill_dtm + bldgs).astype(np.float32)

    # Coarse SRTM DEM: terrain plus coarse regional building envelope
    srtm_dem = hill_dtm.copy()
    srtm_dem += 0.2 * bldgs

    # Estimated nDSM with realistic estimation noise
    np.random.seed(42)
    ndsm_est = np.maximum(0.0, bldgs + np.random.normal(0, 0.3, (H, W))).astype(np.float32)

    return hill_dtm, bldgs, true_dsm, srtm_dem, ndsm_est


def test_path_a_recovers_building_heights_within_2m_rmse() -> None:
    """Acceptance check 1: Known hill + buildings calibrated via Path A recovers heights within 2.0m RMSE."""
    hill_dtm, true_bldgs, true_dsm, srtm_dem, ndsm_est = create_synthetic_hill_and_buildings()

    calibrated_dsm, meta = calibrate_path_a(
        ndsm=ndsm_est,
        srtm_dem=srtm_dem,
        gsd_m=0.33,
        filter_radius_m=6.0,
    )

    assert meta["calibration_path"] == "PATH_A_SRTM_DECOMPOSE"
    assert meta["status"] == "CALIBRATED"
    assert meta["is_absolute"] is True

    # Recovered building heights = calibrated_dsm - decomposed bare-earth DTM
    decomposed_dtm = decompose_bare_earth_dtm(srtm_dem, gsd_m=0.33, filter_radius_m=6.0)
    recovered_bldgs = np.maximum(0.0, calibrated_dsm - decomposed_dtm)

    # Evaluate RMSE across all building footprint pixels
    bldg_mask = true_bldgs > 0.0
    diff = recovered_bldgs[bldg_mask] - true_bldgs[bldg_mask]
    bldg_rmse = float(np.sqrt(np.mean(diff**2)))

    assert bldg_rmse < 2.0, f"Expected building height RMSE < 2.0m, got {bldg_rmse:.3f}m"

    # Overall DSM RMSE against ground truth
    overall_rmse = float(np.sqrt(np.mean((calibrated_dsm - true_dsm) ** 2)))
    assert overall_rmse < 2.0, f"Expected overall DSM RMSE < 2.0m, got {overall_rmse:.3f}m"


def test_path_a_rejects_high_building_density() -> None:
    """Reject Path A when building density exceeds 80% (dense urban canyon)."""
    H, W = 100, 100
    srtm_dem = np.full((H, W), 100.0, dtype=np.float32)
    # 85% of scene covered by buildings
    ndsm_dense = np.zeros((H, W), dtype=np.float32)
    ndsm_dense[:85, :] = 25.0

    dsm, meta = calibrate_path_a(ndsm_dense, srtm_dem, max_building_density=0.80)

    assert meta["status"] == "REJECTED_FALLBACK_TO_PATH_C"
    assert meta["fallback_reason"] == "high_building_density"


def test_path_a_rejects_steep_relief() -> None:
    """Reject Path A when terrain slope exceeds 45 degrees."""
    H, W = 100, 100
    # Steep cliff: rises 200m over 10m width (slope > 60 deg)
    y, x = np.mgrid[0:H, 0:W]
    steep_dem = (x * 20.0).astype(np.float32)
    ndsm = np.zeros((H, W), dtype=np.float32)

    dsm, meta = calibrate_path_a(ndsm, steep_dem, gsd_m=0.33, max_slope_deg=45.0)

    assert meta["status"] == "REJECTED_FALLBACK_TO_PATH_C"
    assert meta["fallback_reason"] == "steep_relief"
