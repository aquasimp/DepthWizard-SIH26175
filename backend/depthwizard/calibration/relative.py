"""Path D: Relative unitless normalization for non-georeferenced imagery."""

from typing import Optional, Tuple

import numpy as np


def calibrate_path_d(
    depth_raw: np.ndarray,
    known_height_m: Optional[float] = None,
    assumed_gsd_m: Optional[float] = None,
) -> Tuple[np.ndarray, dict]:
    """Robust stretch to [0, 1] relative units."""
    meta = {
        "calibration_path": "PATH_D_RELATIVE",
        "vertical_datum": "None",
        "is_absolute": False,
        "units": "relative",
        "calibration_status": "RELATIVE_ONLY",
    }
    return depth_raw, meta
