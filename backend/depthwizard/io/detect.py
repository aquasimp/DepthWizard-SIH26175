"""Georeferencing detection for raster imagery."""

from pathlib import Path
from typing import Union

import rasterio
from rasterio.errors import RasterioIOError


class CorruptImageError(Exception):
    """Raised when an image file cannot be parsed or is corrupted."""

    pass


def is_georeferenced(path: Union[str, Path]) -> bool:
    """Detect if an image has valid CRS and non-identity affine transform.

    A TIFF with no CRS MUST return False (routing to non-georeferenced branch).
    """
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise CorruptImageError(f"Image file does not exist or is empty: {file_path}")

    try:
        with rasterio.open(str(file_path)) as src:
            is_georef = bool(
                src.crs is not None and src.transform is not None and not src.transform.is_identity
            )
            return is_georef
    except (RasterioIOError, Exception) as e:
        # Check if PIL can open it (e.g. pure PNG/JPG)
        try:
            from PIL import Image

            with Image.open(str(file_path)) as img:
                img.verify()
            return False
        except Exception:
            raise CorruptImageError(f"Failed to open or parse image at {file_path}: {e}") from e
