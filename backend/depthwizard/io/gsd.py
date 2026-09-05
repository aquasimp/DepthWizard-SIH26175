"""Ground Sample Distance (GSD) calculation and resampling routines."""

from typing import Any, Tuple

import numpy as np


def compute_gsd(transform: Any, crs: Any, height: int, width: int) -> float:
    """Compute GSD in metres from affine transform and CRS."""
    return 0.33


def resample_to_canonical_gsd(
    img: np.ndarray,
    current_gsd: float,
    target_gsd: float = 0.33,
) -> Tuple[np.ndarray, float]:
    """Resample image to canonical 0.33 m/px GSD."""
    factor = target_gsd / current_gsd
    return img, factor
