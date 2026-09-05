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
            "status": "DEGENERATE_FLAT",
        }
        return dsm, meta

    d_valid = disparity[valid]
    var_d = float(np.var(d_valid))
    p5 = float(np.percentile(d_valid, 5))
    p95 = float(np.percentile(d_valid, 95))
    d_range = p95 - p5

    # Degeneracy guard: flat water, salt flat, or featureless desert
    if var_d < 1e-4 or d_range < 1e-4:
        logger.info("Degeneracy guard triggered: flat water or desert scene (var < 1e-4).")
        base_h = (
            float(np.median(reference_dem[np.isfinite(reference_dem)]))
            if reference_dem is not None and np.any(np.isfinite(reference_dem))
            else 0.0
        )
        dsm = np.full_like(disparity, fill_value=base_h, dtype=np.float32)
        meta = {
            "calibration_path": "PATH_C_RANSAC_AFFINE",
            "vertical_datum": "EGM96",
            "is_absolute": True if reference_dem is not None else False,
            "units": "metres",
            "is_degenerate": True,
            "flat_scene": True,
            "scale": 0.0,
            "shift": round(base_h, 3),
            "status": "DEGENERATE_FLAT",
        }
        return dsm, meta

    # If reference DEM is available and has variation, use RANSAC regressor
    if reference_dem is not None and np.isfinite(reference_dem).any():
        ref_valid = reference_dem[valid]
        if np.var(ref_valid) > 0.1:
            # Sample up to 2000 points for robust RANSAC
            indices = np.random.choice(len(d_valid), size=min(2000, len(d_valid)), replace=False)
            X = d_valid[indices].reshape(-1, 1)
            y = ref_valid[indices]

            try:
                ransac = RANSACRegressor(min_samples=10, residual_threshold=3.0, random_state=42)
                ransac.fit(X, y)
                s = float(ransac.estimator_.coef_[0])
                t = float(ransac.estimator_.intercept_)
                # Ensure positive scale
                if s <= 0:
                    s = typical_structure_height_m / max(1e-3, d_range)
                    t = float(np.median(ref_valid)) - s * p5
            except Exception:
                s = typical_structure_height_m / max(1e-3, d_range)
                t = float(np.median(ref_valid)) - s * p5
        else:
            base_z = float(np.median(ref_valid))
            s = typical_structure_height_m / max(1e-3, d_range)
            t = base_z - s * p5
    else:
        # Building height prior: map 5th percentile to 0m (ground) and 95th percentile to typical structure height
        s = typical_structure_height_m / max(1e-3, d_range)
        t = -s * p5

    calibrated_dsm = np.maximum(0.0, s * disparity + t).astype(np.float32)

    meta = {
        "calibration_path": "PATH_C_RANSAC_AFFINE",
        "vertical_datum": "EGM96",
        "is_absolute": True if reference_dem is not None else False,
        "units": "metres",
        "is_degenerate": False,
        "flat_scene": False,
        "scale": round(s, 4),
        "shift": round(t, 4),
        "status": "CALIBRATED",
    }
    return calibrated_dsm, meta
