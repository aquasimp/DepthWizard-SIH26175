"""Ground Sample Distance (GSD) calculation and canonical resampling."""

from typing import Any, Dict, Tuple

import cv2
import numpy as np


def compute_gsd(
    transform: Any,
    crs: Any,
    height: int,
    width: int,
    assumed_gsd_m: float = 0.33,
) -> float:
    """Compute GSD in metres from affine transform and CRS.

    If CRS is geographic (degrees), converts to metres at scene-centre latitude.
    If no CRS, returns assumed_gsd_m.
    """
    if transform is None or crs is None or getattr(transform, "is_identity", False):
        return float(assumed_gsd_m)

    # Pixel dimensions from transform
    # Transform: (a, b, c, d, e, f) where a=px_width, e=px_height (typically negative)
    a = float(transform.a)
    e = float(transform.e)
    px_w = abs(a)
    px_h = abs(e)

    # Check if CRS is geographic (degrees)
    is_geographic = False
    if hasattr(crs, "is_geographic"):
        is_geographic = bool(crs.is_geographic)
    elif hasattr(crs, "to_epsg"):
        epsg = crs.to_epsg()
        if epsg == 4326:
            is_geographic = True

    if is_geographic:
        # Latitude at scene center
        f = float(transform.f)
        lat_top = f
        lat_bottom = f + height * e
        center_lat = 0.5 * (lat_top + lat_bottom)

        # Metres per degree
        # 1 deg latitude ≈ 111,320 m
        # 1 deg longitude ≈ 111,320 m * cos(lat)
        lat_rad = np.radians(np.clip(center_lat, -85.0, 85.0))
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * float(np.cos(lat_rad))

        dx_m = px_w * m_per_deg_lon
        dy_m = px_h * m_per_deg_lat
        gsd_m = float(0.5 * (dx_m + dy_m))
    else:
        # Projected CRS (already in metres or survey units)
        gsd_m = float(0.5 * (px_w + px_h))

    return max(1e-4, gsd_m)


def resample_to_canonical_gsd(
    image: np.ndarray,
    current_gsd: float,
    target_gsd: float = 0.33,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Resample image to canonical 0.33 m/px GSD.

    Uses INTER_AREA when downsampling and INTER_CUBIC when upsampling.

    Returns:
        resampled_image: np.ndarray
        meta: dict containing original_gsd, target_gsd, resample_factor
    """
    resample_factor = float(current_gsd / target_gsd)
    h, w = image.shape[:2]

    # If already at target GSD within 1% tolerance, no resampling needed
    if abs(resample_factor - 1.0) < 0.01:
        return image, {
            "original_gsd": round(current_gsd, 4),
            "target_gsd": round(target_gsd, 4),
            "resample_factor": 1.0,
        }

    new_w = max(1, int(round(w * resample_factor)))
    new_h = max(1, int(round(h * resample_factor)))

    if resample_factor > 1.0:
        # Upsampling (more pixels) -> INTER_CUBIC
        interpolation = cv2.INTER_CUBIC
    else:
        # Downsampling (fewer pixels) -> INTER_AREA
        interpolation = cv2.INTER_AREA

    resampled = cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    meta = {
        "original_gsd": round(current_gsd, 4),
        "target_gsd": round(target_gsd, 4),
        "resample_factor": round(resample_factor, 4),
    }
    return resampled, meta
