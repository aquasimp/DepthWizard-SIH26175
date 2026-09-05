"""Geospatial raster and 16-bit heightmap writers."""

from pathlib import Path
from typing import Any, Dict, Union

import numpy as np


def write_geotiff(
    path: Union[str, Path],
    data: np.ndarray,
    crs: Any,
    transform: Any,
    nodata: float = -9999.0,
    description: str = "DSM_absolute_metres_EGM96",
) -> None:
    """Write float32 GeoTIFF with LZW compression and tiling."""
    pass


def write_16bit_heightmap(
    png_path: Union[str, Path],
    json_path: Union[str, Path],
    heights: np.ndarray,
    metadata: Dict[str, Any],
) -> None:
    """Write 16-bit PNG heightmap and sidecar metadata."""
    pass
