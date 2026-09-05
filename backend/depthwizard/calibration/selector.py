"""Calibration path selector and execution logic."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from depthwizard.calibration.dtm_decompose import calibrate_path_a
from depthwizard.calibration.gcp_fit import calibrate_path_b
from depthwizard.calibration.ransac_affine import calibrate_path_c
from depthwizard.calibration.relative import calibrate_path_d
from depthwizard.calibration.srtm import fetch_srtm_dem
from depthwizard.utils.logging import logger


def select_calibration_path(
    is_georef: bool,
    has_gcps: bool = False,
    has_srtm: bool = False,
    building_density: Optional[float] = None,
    terrain_slope_deg: Optional[float] = None,
) -> str:
    """Select appropriate calibration path (A, B, C, or D).

    Selection Hierarchy:
    1. PATH_B: If ground control points (GCPs) are supplied.
    2. PATH_A: If georeferenced and SRTM DEM is available (and building density <= 80% and slope <= 45 deg).
    3. PATH_C: If georeferenced without SRTM, or if Path A conditions are rejected.
    4. PATH_D: If imagery is unreferenced (consumer PNG/JPEG).
    """
    if has_gcps:
        return "PATH_B"

    if is_georef:
        if has_srtm:
            if building_density is not None and building_density > 0.80:
                return "PATH_C"
            if terrain_slope_deg is not None and terrain_slope_deg > 45.0:
                return "PATH_C"
            return "PATH_A"
        return "PATH_C"

    return "PATH_D"


def calibrate_scene(
    disparity: np.ndarray,
    is_georeferenced: bool,
    crs: Any = None,
    transform: Any = None,
    bounds: Optional[List[float]] = None,
    gcps: Optional[List[Dict[str, float]]] = None,
    reference_dsm: Optional[np.ndarray] = None,
    explicit_path: Optional[str] = None,
    gsd_m: float = 0.33,
) -> Tuple[np.ndarray, Optional[np.ndarray], Dict[str, Any]]:
    """Execute end-to-end scale calibration based on data availability and hierarchy.

    Args:
        disparity: Raw disparity / relative depth map from model inference.
        is_georeferenced: Whether input has spatial reference.
        crs: Rasterio CRS.
        transform: Affine transform.
        bounds: Bounding box [left, bottom, right, top].
        gcps: List of ground control points dicts [{'x': ..., 'y': ..., 'z_true': ...}].
        reference_dsm: Optional reference DSM array for Path C.
        explicit_path: Force specific path ('PATH_A', 'PATH_B', 'PATH_C', 'PATH_D').
        gsd_m: Spatial resolution in metres.

    Returns:
        Tuple of (calibrated_dsm, ndsm_or_none, metadata_dict).
    """
    h, w = disparity.shape[:2]

    # Check for GCPs (Path B)
    if (explicit_path == "PATH_B" or (explicit_path is None and gcps and len(gcps) >= 3)):
        try:
            cal_dsm, b_meta = calibrate_path_b(disparity, gcps or [])
            return cal_dsm, disparity, {"path": "PATH_B", **b_meta}
        except Exception as e:
            logger.warning(f"Path B calibration failed: {e}. Falling back to hierarchy.")

    # Check Path A (SRTM + DTM decomposition)
    if is_georeferenced and explicit_path in (None, "PATH_A"):
        srtm_dem = None
        if bounds is not None and len(bounds) >= 4 and crs is not None:
            try:
                b_tuple = (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))
                srtm_dem = fetch_srtm_dem(
                    bounds=b_tuple,
                    target_shape=(h, w),
                    target_crs=crs,
                    target_transform=transform,
                )
            except Exception as e:
                logger.warning(f"Failed to fetch SRTM DEM: {e}")

        if srtm_dem is not None and np.any(np.isfinite(srtm_dem)):
            try:
                cal_dsm, a_meta = calibrate_path_a(disparity, srtm_dem, gsd_m=gsd_m)
                ndsm = np.maximum(0.0, disparity).astype(np.float32)
                return cal_dsm, ndsm, {"path": "PATH_A", **a_meta}
            except Exception as e:
                logger.warning(f"Path A processing failed: {e}. Falling back.")

    # Path C (RANSAC Disparity Fit / Degeneracy Guard)
    if is_georeferenced or explicit_path == "PATH_C":
        try:
            cal_dsm, c_meta = calibrate_path_c(disparity, reference_dem=reference_dsm)
            ndsm = np.maximum(0.0, disparity).astype(np.float32)
            return cal_dsm, ndsm, {"path": "PATH_C", **c_meta}
        except Exception as e:
            logger.warning(f"Path C failed: {e}. Falling back to Path D.")

    # Path D (Relative Stretch)
    rel_dsm, d_meta = calibrate_path_d(disparity)
    return rel_dsm, None, {"path": "PATH_D", **d_meta}
