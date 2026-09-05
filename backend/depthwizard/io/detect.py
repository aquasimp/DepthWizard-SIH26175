"""Georeferencing detection for raster imagery."""

from pathlib import Path
from typing import Union

import rasterio


class CorruptImageError(Exception):
    """Raised when an image cannot be parsed by rasterio/GDAL."""
    pass


def is_georeferenced(path: Union[str, Path]) -> bool:
    """Detect if an image has valid CRS and non-identity affine transform."""
    try:
        with rasterio.open(str(path)) as src:
            is_georef = bool(
                src.crs is not None
                and src.transform is not None
                and not src.transform.is_identity
            )
            return is_georef
    except Exception as e:
        raise CorruptImageError(f"Failed to open or parse image at {path}: {e}") from e
