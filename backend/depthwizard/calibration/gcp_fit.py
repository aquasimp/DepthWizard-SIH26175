"""Path B: Ground Control Point (GCP) affine reference fitting."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import HuberRegressor

from depthwizard.utils.logging import logger


class InsufficientGCPsError(ValueError):
    """Raised when fewer than 3 GCPs are provided."""

    pass


class CollinearGCPsError(ValueError):
    """Raised when GCP coordinates are degenerate/collinear."""

    pass


def check_gcp_collinearity(coords: np.ndarray, tolerance: float = 1e-4) -> bool:
    """Return True if points in (N, 2) coords array are collinear."""
    if len(coords) < 3:
        return True
    centered = coords - coords.mean(axis=0)
    # Singular value decomposition
    _, s, _ = np.linalg.svd(centered)
    # If ratio of smaller singular value to larger is below tolerance, points are collinear
    if s[0] < 1e-7:
        return True
    return bool((s[1] / s[0]) < tolerance)


def calibrate_path_b(
    dsm_initial: np.ndarray,
    gcps: List[Dict[str, float]],
    bounds: Optional[Tuple[float, float, float, float]] = None,
    transform: Any = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Path B: Calibrate elevation model using Ground Control Points with Huber regression.

    Args:
        dsm_initial: (H, W) float32 unscaled elevation or relative disparity.
        gcps: List of dicts with keys 'x', 'y' (pixel coords or projected) and 'z_m' (true height).
        bounds: Optional scene bounds.
        transform: Optional affine transform.

    Returns:
        calibrated_dsm: (H, W) float32 metric elevation model.
        meta: Metadata dict.
    """
    H, W = dsm_initial.shape[:2]

    # Validation: Count check
    if len(gcps) < 3:
        logger.warning(f"Path B rejected: only {len(gcps)} GCPs provided (minimum 3 required).")
        from depthwizard.calibration.ransac_affine import calibrate_path_c

        dsm_fallback, meta_c = calibrate_path_c(dsm_initial, dsm_initial)
        meta_c["fallback_reason"] = "insufficient_gcps"
        meta_c["status"] = "REJECTED_FALLBACK_TO_PATH_C"
        return dsm_fallback, meta_c

    # Extract coordinates
    pts = []
    z_true = []
    for g in gcps:
        x_val = g.get("x", g.get("lon", 0.0))
        y_val = g.get("y", g.get("lat", 0.0))
        z_val = g["z_m"]

        # If transform is provided and coordinates are in map CRS, convert to pixel (col, row)
        if transform is not None and (abs(x_val) > W or abs(y_val) > H):
            inv_t = ~transform
            px, py = inv_t * (x_val, y_val)
        else:
            px, py = x_val, y_val

        pts.append([px, py])
        z_true.append(z_val)

    pts_arr = np.array(pts, dtype=np.float64)
    z_arr = np.array(z_true, dtype=np.float64)

    # Validation: Collinearity check
    if check_gcp_collinearity(pts_arr):
        logger.warning("Path B rejected: GCP points are collinear. Triggering fallback to Path C.")
        from depthwizard.calibration.ransac_affine import calibrate_path_c

        dsm_fallback, meta_c = calibrate_path_c(dsm_initial, dsm_initial)
        meta_c["fallback_reason"] = "collinear_gcps"
        meta_c["status"] = "REJECTED_FALLBACK_TO_PATH_C"
        return dsm_fallback, meta_c

    # Sample dsm_initial at GCP pixel locations
    d_sampled = []
    valid_mask = []
    for px, py in pts_arr:
        col = int(np.clip(round(px), 0, W - 1))
        row = int(np.clip(round(py), 0, H - 1))
        val = dsm_initial[row, col]
        if np.isfinite(val):
            d_sampled.append(val)
            valid_mask.append(True)
        else:
            d_sampled.append(0.0)
            valid_mask.append(False)

    d_arr = np.array(d_sampled, dtype=np.float64)
    valid_idx = np.array(valid_mask, dtype=bool)

    if np.sum(valid_idx) < 3:
        logger.warning("Path B rejected: fewer than 3 GCPs fall on valid pixels.")
        from depthwizard.calibration.ransac_affine import calibrate_path_c

        dsm_fallback, meta_c = calibrate_path_c(dsm_initial, dsm_initial)
        meta_c["fallback_reason"] = "invalid_pixel_gcps"
        meta_c["status"] = "REJECTED_FALLBACK_TO_PATH_C"
        return dsm_fallback, meta_c

    X = d_arr[valid_idx].reshape(-1, 1)
    y = z_arr[valid_idx]

    # Fit Huber Regressor (robust to outlier GCPs)
    huber = HuberRegressor(epsilon=1.35)
    huber.fit(X, y)
    s = float(huber.coef_[0])
    t = float(huber.intercept_)

    # Calculate GCP RMSE
    preds = huber.predict(X)
    gcp_rmse = float(np.sqrt(np.mean((preds - y) ** 2)))

    calibrated_dsm = (s * dsm_initial + t).astype(np.float32)

    meta = {
        "calibration_path": "PATH_B_GCP_REFINEMENT",
        "vertical_datum": "EGM96",
        "is_absolute": True,
        "units": "metres",
        "gcp_count": len(gcps),
        "scale": round(s, 4),
        "shift": round(t, 4),
        "gcp_rmse_m": round(gcp_rmse, 3),
        "status": "CALIBRATED",
    }
    return calibrated_dsm, meta
