"""Tests for Path B: GCP affine reference fitting (Acceptance check 2)."""

import numpy as np
import pytest
from depthwizard.calibration.gcp_fit import (
    calibrate_path_b,
    check_gcp_collinearity,
)


def test_path_b_5_gcps_recovers_heights_within_half_metre_rmse() -> None:
    """Acceptance check 2: 5 synthetic GCPs recover true metric heights within 0.5m RMSE."""
    H, W = 100, 100
    y, x = np.mgrid[0:H, 0:W]

    # True metric elevation surface (sloping terrain + features)
    z_true = (30.0 + 0.08 * x + 0.12 * y).astype(np.float32)
    # Add a couple structure blocks
    z_true[20:40, 20:40] += 15.0
    z_true[60:75, 60:75] += 20.0

    # Model disparity: unscaled relative representation
    # z_true = 14.5 * d + 12.0  => d = (z_true - 12.0) / 14.5
    true_s = 14.5
    true_t = 12.0
    disparity = ((z_true - true_t) / true_s).astype(np.float32)

    # 5 distributed, non-collinear Ground Control Points
    gcp_coords = [
        (15, 15),
        (85, 20),
        (50, 50),
        (20, 80),
        (80, 85),
    ]

    gcps = []
    np.random.seed(123)
    for px, py in gcp_coords:
        # Survey height with minor survey error (+/- 0.05m)
        z_survey = float(z_true[py, px]) + float(np.random.normal(0, 0.03))
        gcps.append(
            {
                "x": float(px),
                "y": float(py),
                "z_m": z_survey,
            }
        )

    calibrated_dsm, meta = calibrate_path_b(
        dsm_initial=disparity,
        gcps=gcps,
    )

    assert meta["calibration_path"] == "PATH_B_GCP_REFINEMENT"
    assert meta["status"] == "CALIBRATED"
    assert meta["gcp_count"] == 5

    # Check scale and shift recovery
    assert pytest.approx(meta["scale"], rel=0.05) == true_s
    assert pytest.approx(meta["shift"], rel=0.05) == true_t

    # Check overall scene RMSE
    scene_rmse = float(np.sqrt(np.mean((calibrated_dsm - z_true) ** 2)))
    assert scene_rmse < 0.5, f"Expected scene RMSE < 0.5m, got {scene_rmse:.3f}m"

    # Check GCP residual RMSE
    assert meta["gcp_rmse_m"] < 0.5


def test_path_b_rejects_insufficient_gcps() -> None:
    """Fewer than 3 GCPs must trigger fallback to Path C."""
    H, W = 50, 50
    disp = np.ones((H, W), dtype=np.float32)
    # Only 2 GCPs
    gcps = [
        {"x": 10.0, "y": 10.0, "z_m": 25.0},
        {"x": 40.0, "y": 40.0, "z_m": 35.0},
    ]

    dsm, meta = calibrate_path_b(disp, gcps)
    assert meta["status"] == "REJECTED_FALLBACK_TO_PATH_C"
    assert meta["fallback_reason"] == "insufficient_gcps"


def test_path_b_rejects_collinear_gcps() -> None:
    """Collinear GCPs must trigger fallback to Path C."""
    H, W = 50, 50
    disp = np.ones((H, W), dtype=np.float32)
    # 4 strictly collinear points on diagonal line y = x
    gcps = [
        {"x": 10.0, "y": 10.0, "z_m": 20.0},
        {"x": 20.0, "y": 20.0, "z_m": 25.0},
        {"x": 30.0, "y": 30.0, "z_m": 30.0},
        {"x": 40.0, "y": 40.0, "z_m": 35.0},
    ]

    pts = np.array([[g["x"], g["y"]] for g in gcps])
    assert check_gcp_collinearity(pts) is True

    dsm, meta = calibrate_path_b(disp, gcps)
    assert meta["status"] == "REJECTED_FALLBACK_TO_PATH_C"
    assert meta["fallback_reason"] == "collinear_gcps"
