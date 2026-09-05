"""Raster image reader normalizing all inputs to 3-band uint8 RGB."""

from pathlib import Path
from typing import Any, Dict, Tuple, Union

import numpy as np
import rasterio
from PIL import Image

from depthwizard.io.detect import CorruptImageError
from depthwizard.io.gsd import compute_gsd


class NonNorthUpError(Exception):
    """Raised when an affine transform includes shear or rotation."""

    pass


class ImageDimensionExceededError(Exception):
    """Raised when image dimensions exceed MAX_UPLOAD_PX."""

    pass


def read_image_rgb(
    path: Union[str, Path],
    max_upload_px: int = 8000,
    assumed_gsd_m: float = 0.33,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Read any geospatial or standard image, normalizing to 3-band uint8 RGB.

    Handles:
    - 16-bit rasters
    - Palette / indexed color
    - >3 bands (extracts RGB channels)
    - Rejects non-north-up (rotated/sheared) transforms
    - Rejects inputs exceeding max_upload_px

    Returns:
        rgb: (H, W, 3) uint8 numpy array
        metadata: Dict containing crs, transform, gsd, is_georeferenced
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Image not found at {file_path}")

    # Try opening via rasterio first
    try:
        with rasterio.open(str(file_path)) as src:
            h, w = src.height, src.width
            if h > max_upload_px or w > max_upload_px:
                raise ImageDimensionExceededError(
                    f"Image dimensions ({w}x{h}) exceed maximum allowed {max_upload_px}x{max_upload_px} px."
                )

            # Check rotation / shear in affine transform
            if src.transform is not None and not src.transform.is_identity:
                b = float(src.transform.b)
                d = float(src.transform.d)
                if abs(b) > 1e-7 or abs(d) > 1e-7:
                    raise NonNorthUpError(
                        f"Image transform contains rotation or shear (b={b}, d={d}). "
                        "Only north-up imagery is supported."
                    )

            is_georef = bool(
                src.crs is not None and src.transform is not None and not src.transform.is_identity
            )

            # Read channels
            count = src.count
            if count >= 3:
                r = src.read(1)
                g = src.read(2)
                b_band = src.read(3)
                raw_rgb = np.stack([r, g, b_band], axis=-1)
            elif count == 1:
                band1 = src.read(1)
                raw_rgb = np.stack([band1, band1, band1], axis=-1)
            else:
                band1 = src.read(1)
                band2 = src.read(2)
                raw_rgb = np.stack([band1, band2, band1], axis=-1)

            # Handle dtype normalization to uint8
            if raw_rgb.dtype == np.uint8:
                rgb = raw_rgb
            elif raw_rgb.dtype in [np.uint16, np.int16]:
                # 16-bit normalization
                val_max = float(raw_rgb.max())
                if val_max > 255.0:
                    rgb = np.clip(raw_rgb / 256.0, 0, 255).astype(np.uint8)
                else:
                    rgb = raw_rgb.astype(np.uint8)
            elif np.issubdtype(raw_rgb.dtype, np.floating):
                val_max = float(raw_rgb.max())
                if val_max <= 1.0:
                    rgb = np.clip(raw_rgb * 255.0, 0, 255).astype(np.uint8)
                else:
                    rgb = np.clip(raw_rgb, 0, 255).astype(np.uint8)
            else:
                rgb = raw_rgb.astype(np.uint8)

            crs_str = str(src.crs) if src.crs else None
            transform = src.transform

            metadata: Dict[str, Any] = {
                "width": w,
                "height": h,
                "is_georeferenced": is_georef,
                "crs": crs_str,
                "crs_obj": src.crs,
                "transform": transform,
                "bounds": list(src.bounds) if is_georef else None,
                "driver": src.driver,
                "gsd": compute_gsd(transform, src.crs, h, w, assumed_gsd_m=assumed_gsd_m),
            }
            return rgb, metadata

    except (NonNorthUpError, ImageDimensionExceededError):
        raise
    except Exception:
        # Fallback to PIL (handles palette, JPEG, standard PNG)
        pass

    try:
        with Image.open(str(file_path)) as img:
            w, h = img.size
            if h > max_upload_px or w > max_upload_px:
                raise ImageDimensionExceededError(
                    f"Image dimensions ({w}x{h}) exceed maximum allowed {max_upload_px}x{max_upload_px} px."
                )

            # Convert palette/RGBA/grayscale to RGB
            rgb_img = img.convert("RGB")
            rgb = np.array(rgb_img, dtype=np.uint8)

            metadata = {
                "width": w,
                "height": h,
                "is_georeferenced": False,
                "crs": None,
                "crs_obj": None,
                "transform": None,
                "bounds": None,
                "driver": img.format,
                "gsd": float(assumed_gsd_m),
            }
            return rgb, metadata
    except (NonNorthUpError, ImageDimensionExceededError):
        raise
    except Exception as e:
        raise CorruptImageError(f"Failed to read image at {file_path}: {e}") from e
