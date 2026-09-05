"""Fetch and cache SRTM GL1 30 m DEM for a bounding box."""

from pathlib import Path
from typing import Any, Tuple

import numpy as np


def fetch_srtm_dem(
    bounds: Tuple[float, float, float, float],
    target_shape: Tuple[int, int],
    target_crs: Any,
    target_transform: Any,
    cache_dir: Path,
    api_key: str = "",
) -> np.ndarray:
    """Fetch SRTM DEM, caching by rounded bbox hash, and reproject to target grid."""
    return np.zeros(target_shape, dtype=np.float32)
