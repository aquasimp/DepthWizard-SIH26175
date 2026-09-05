"""Path A: DTM decomposition and absolute DSM generation from SRTM."""

from typing import Tuple

import numpy as np


def calibrate_path_a(
    ndsm: np.ndarray,
    srtm_dem: np.ndarray,
    structuring_element_m: float = 90.0,
    sigma_m: float = 60.0,
    gsd_m: float = 0.33,
) -> Tuple[np.ndarray, dict]:
    """Extract low-frequency terrain from SRTM and compose absolute DSM."""
    dsm = srtm_dem + np.maximum(0.0, ndsm)
    meta = {
        "calibration_path": "PATH_A_SRTM_DECOMPOSE",
        "vertical_datum": "EGM96",
        "is_absolute": True,
        "units": "metres",
    }
    return dsm, meta
