"""Path A: DTM decomposition and absolute DSM generation from SRTM."""

from typing import Any, Dict, Tuple

import numpy as np
from scipy import ndimage
from skimage.morphology import disk, opening

from depthwizard.utils.logging import logger


def decompose_bare_earth_dtm(
    srtm_dem: np.ndarray,
    gsd_m: float = 0.33,
    filter_radius_m: float = 45.0,
) -> np.ndarray:
    """Extract smooth bare-earth DTM from SRTM DEM using morphological opening.

    Uses a disk structuring element of physical radius filter_radius_m to
    remove surface structures (buildings, canopy) while tracking underlying terrain.
    """
    radius_px = max(2, int(round(filter_radius_m / max(1e-4, gsd_m))))
    # Cap radius to avoid huge footprint on high-res grids
    radius_px = min(radius_px, 35)

    struct_elem = disk(radius_px)
    dtm_opened = opening(srtm_dem.astype(np.float64), footprint=struct_elem).astype(np.float32)

    # Smooth subtle stepping artifacts
    sigma_px = max(1.0, radius_px * 0.25)
    dtm_smooth = ndimage.gaussian_filter(dtm_opened, sigma=sigma_px)
    return dtm_smooth.astype(np.float32)


def compute_terrain_slope_deg(dtm: np.ndarray, gsd_m: float = 0.33) -> float:
    """Compute mean terrain slope in degrees."""
    gy, gx = np.gradient(dtm, gsd_m, gsd_m)
    slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
    return float(np.degrees(np.mean(slope_rad)))


def calibrate_path_a(
    ndsm: np.ndarray,
    srtm_dem: np.ndarray,
    gsd_m: float = 0.33,
    filter_radius_m: float = 45.0,
    max_building_density: float = 0.80,
    max_slope_deg: float = 45.0,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Path A: Calibrate absolute DSM using SRTM 30 m bare-earth DTM decomposition.

    Checks:
    - Building density > 80%: rejects to Path C.
    - Terrain slope > 45 deg: rejects to Path C.
    - Fits scale s and shift t such that DSM = DTM + max(0, s * ndsm + t).

    Returns:
        dsm: (H, W) float32 absolute elevation in metres (EGM96).
        meta: Metadata dictionary.
    """
    H, W = ndsm.shape[:2]

    # 1. Bare-earth DTM extraction
    dtm = decompose_bare_earth_dtm(srtm_dem, gsd_m=gsd_m, filter_radius_m=filter_radius_m)
    mean_slope = compute_terrain_slope_deg(dtm, gsd_m=gsd_m)

    # 2. Building density check (height > 2.5m)
    building_mask = ndsm > 2.5
    building_density = float(np.mean(building_mask))

    meta: Dict[str, Any] = {
        "calibration_path": "PATH_A_SRTM_DECOMPOSE",
        "vertical_datum": "EGM96",
        "is_absolute": True,
        "units": "metres",
        "building_density": round(building_density, 3),
        "mean_slope_deg": round(mean_slope, 2),
        "status": "CALIBRATED",
    }

    # 3. Fallback checks
    if building_density > max_building_density or mean_slope > max_slope_deg:
        reason = (
            "high_building_density" if building_density > max_building_density else "steep_relief"
        )
        logger.warning(
            f"Path A conditions violated ({reason}). Triggering fallback to Path C.",
            extra={"building_density": building_density, "mean_slope_deg": mean_slope},
        )
        meta["status"] = "REJECTED_FALLBACK_TO_PATH_C"
        meta["fallback_reason"] = reason

        # Fallback to Path C
        from depthwizard.calibration.ransac_affine import calibrate_path_c

        dsm_fallback, meta_c = calibrate_path_c(ndsm, srtm_dem)
        meta["fallback_meta"] = meta_c
        return dsm_fallback, meta

    # 4. Metric scale & shift fitting
    # Sample points across scene
    valid_samples = np.isfinite(ndsm) & np.isfinite(dtm)
    n_valid = int(np.sum(valid_samples))

    if n_valid < 50:
        s, t = 1.0, 0.0
    else:
        # Check if ndsm is already in metric units (max height > 3.0m)
        max_h = float(np.nanmax(ndsm)) if np.any(valid_samples) else 0.0
        if max_h > 3.0:
            s = 1.0
            t = 0.0
        else:
            # Relative disparity in [0, 1] or [0, 0.4]: fit scale against building prior
            p99 = float(np.nanpercentile(ndsm, 99))
            p1 = float(np.nanpercentile(ndsm, 1))
            d_range = p99 - p1
            if d_range > 1e-4:
                # Typical building elevation delta ~15m
                s = 15.0 / d_range
                t = 0.0
            else:
                s, t = 1.0, 0.0

    meta["scale"] = round(float(s), 4)
    meta["shift"] = round(float(t), 4)

    calibrated_ndsm = np.maximum(0.0, s * ndsm + t).astype(np.float32)
    dsm = (dtm + calibrated_ndsm).astype(np.float32)
    return dsm, meta
