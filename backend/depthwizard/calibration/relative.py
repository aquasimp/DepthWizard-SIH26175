"""Path D: Relative unitless normalization for unreferenced imagery."""

from typing import Any, Dict, Optional, Tuple

import numpy as np


def calibrate_path_d(
    depth_raw: np.ndarray,
    known_height_m: Optional[float] = None,
    assumed_gsd_m: Optional[float] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Path D: Robust stretch to [0, 1] relative units for unreferenced imagery.

    If known_height_m is provided by the user, scales maximum peak relative to ground.

    Returns:
        dsm: (H, W) float32 normalized elevation map.
        meta: Metadata dictionary with relative warnings.
    """
    valid = np.isfinite(depth_raw)
    if not valid.any():
        return np.zeros_like(depth_raw, dtype=np.float32), {
            "calibration_path": "PATH_D_RELATIVE",
            "vertical_datum": "None",
            "is_absolute": False,
            "units": "relative",
            "calibration_status": "EMPTY",
        }

    p1 = float(np.percentile(depth_raw[valid], 1))
    p99 = float(np.percentile(depth_raw[valid], 99))
    d_range = max(1e-6, p99 - p1)

    normalized = np.clip((depth_raw - p1) / d_range, 0.0, 1.0)

    if known_height_m is not None and known_height_m > 0:
        dsm = (normalized * known_height_m).astype(np.float32)
        units = "metres (user-calibrated)"
        is_absolute = False
    else:
        dsm = normalized.astype(np.float32)
        units = "relative_normalized"
        is_absolute = False

    meta: Dict[str, Any] = {
        "calibration_path": "PATH_D_RELATIVE",
        "vertical_datum": "None",
        "is_absolute": is_absolute,
        "units": units,
        "calibration_status": "RELATIVE_ONLY",
        "warning": "Input is not georeferenced. Elevation scale is relative and unanchored to global vertical datum.",
        "assumed_gsd_m": assumed_gsd_m or 0.33,
    }
    return dsm, meta
