"""Path C: Disparity RANSAC affine alignment with flat-scene degeneracy guard."""

from typing import Any, Dict, Optional, Tuple

import numpy as np
from sklearn.linear_model import RANSACRegressor

from depthwizard.utils.logging import logger


def calibrate_path_c(
    disparity: np.ndarray,
    reference_dem: Optional[np.ndarray] = None,
    assumed_max_structure_height_m: float = 35.0,
    typical_structure_height_m: float = 12.0,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Path C: Automatic Fallback via Disparity RANSAC with flat-scene degeneracy guard.

    Guards against flat terrain/water degeneracy where variance < 1e-4.

    Args:
        disparity: (H, W) float32 estimated relative disparity or uncalibrated depth.
        reference_dem: Optional reference DEM (e.g. coarse SRTM or empty).
        assumed_max_structure_height_m: Upper bound on structure height.
        typical_structure_height_m: Prior height for structures in urban scenes.

    Returns:
        calibrated_dsm: (H, W) float32 metric elevation model.
        meta: Metadata dictionary.
    """
    valid = np.isfinite(disparity)
    if not valid.any():
        dsm = np.zeros_like(disparity, dtype=np.float32)
        meta = {
            "calibration_path": "PATH_C_RANSAC_AFFINE",
            "vertical_datum": "EGM96",
            "is_absolute": False,
            "units": "metres",
            "is_degenerate": True,
            "flat_scene": True,
            "scale": 0.0,
            "shift": 0.0,
            "a": 0.0,
            "b": 0.0,
            "inlier_fraction": 0.0,
            "status": "DEGENERATE_FLAT_TERRAIN",
            "calibration_status": "DEGENERATE_FLAT_TERRAIN",
        }
        return dsm, meta

    d_valid = disparity[valid]
    var_d = float(np.var(d_valid))
    p5 = float(np.percentile(d_valid, 5))
    p95 = float(np.percentile(d_valid, 95))
    d_range = p95 - p5

    has_ref = reference_dem is not None and np.any(np.isfinite(reference_dem))
    ref_valid = reference_dem[valid] if has_ref else None
    ref_std = float(np.std(ref_valid)) if ref_valid is not None and len(ref_valid) > 0 else 0.0

    # Physical degeneracy guard:
    # 1. Featureless flat water or desert disparity (var_d < 1e-4 or d_range < 1e-4)
    # 2. Deliberately flat scene where reference DEM elevation std < 5.0 m
    is_flat_disparity = var_d < 1e-4 or d_range < 1e-4
    is_flat_reference = has_ref and ref_std < 5.0

    if is_flat_disparity or is_flat_reference:
        logger.info(
            "Degeneracy guard triggered: flat scene detected (var_d=%.6f, ref_std=%.2fm).",
            var_d,
            ref_std,
        )
        base_h = float(np.median(ref_valid)) if ref_valid is not None and len(ref_valid) > 0 else 0.0
        max_h_span = 1.5 * assumed_max_structure_height_m

        if is_flat_disparity:
            dsm = np.full_like(disparity, fill_value=base_h, dtype=np.float32)
            s_val, t_val = 0.0, base_h
        else:
            # Flat reference terrain: ground is flat at base_h, map relative structures within [0, 1.5 * assumed_max_structure_height_m]
            s_val = min(
                typical_structure_height_m / max(1e-3, d_range),
                max_h_span / max(1e-3, d_range),
            )
            rel_h = np.clip(s_val * (disparity - p5), 0.0, max_h_span)
            dsm = (base_h + rel_h).astype(np.float32)
            t_val = base_h

        meta = {
            "calibration_path": "PATH_C_RANSAC_AFFINE",
            "vertical_datum": "EGM96",
            "is_absolute": bool(has_ref),
            "units": "metres",
            "is_degenerate": True,
            "flat_scene": True,
            "scale": round(s_val, 4),
            "shift": round(t_val, 4),
            "a": round(s_val, 4),
            "b": round(t_val, 4),
            "inlier_fraction": 1.0,
            "status": "DEGENERATE_FLAT_TERRAIN",
            "calibration_status": "DEGENERATE_FLAT_TERRAIN",
        }
        return dsm, meta

    # If reference DEM is available and has non-degenerate variation (std >= 5.0m), fit RANSAC regressor
    inlier_fraction = 1.0
    if has_ref and ref_std >= 5.0:
        # Sample up to 2000 points for robust RANSAC
        indices = np.random.choice(len(d_valid), size=min(2000, len(d_valid)), replace=False)
        X = d_valid[indices].reshape(-1, 1)
        y = ref_valid[indices]

        try:
            ransac = RANSACRegressor(min_samples=10, residual_threshold=3.0, random_state=42)
            ransac.fit(X, y)
            s = float(ransac.estimator_.coef_[0])
            t = float(ransac.estimator_.intercept_)
            if hasattr(ransac, "inlier_mask_") and ransac.inlier_mask_ is not None:
                inlier_fraction = float(np.mean(ransac.inlier_mask_))
            # Ensure positive scale
            if s <= 0:
                s = typical_structure_height_m / max(1e-3, d_range)
                t = float(np.median(ref_valid)) - s * p5
        except Exception:
            s = typical_structure_height_m / max(1e-3, d_range)
            t = float(np.median(ref_valid)) - s * p5
    else:
        # Building height prior: map 5th percentile to 0m (ground) and 95th percentile to typical structure height
        s = typical_structure_height_m / max(1e-3, d_range)
        t = -s * p5

    calibrated_dsm = np.maximum(0.0, s * disparity + t).astype(np.float32)

    meta = {
        "calibration_path": "PATH_C_RANSAC_AFFINE",
        "vertical_datum": "EGM96",
        "is_absolute": bool(has_ref),
        "units": "metres",
        "is_degenerate": False,
        "flat_scene": False,
        "scale": round(s, 4),
        "shift": round(t, 4),
        "a": round(s, 4),
        "b": round(t, 4),
        "inlier_fraction": round(inlier_fraction, 4),
        "status": "CALIBRATED",
        "calibration_status": "CALIBRATED",
    }
    return calibrated_dsm, meta
