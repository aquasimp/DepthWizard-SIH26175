"""Calibration path selector logic."""

from typing import Optional


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
