"""Vertical datum handling and geoid undulation utilities (EGM96 / WGS84)."""

from typing import Any, Dict

import numpy as np


def compute_approx_egm96_undulation(lat: float, lon: float) -> float:
    """Compute approximate EGM96 geoid undulation N (metres) for (lat, lon).

    h_ellipsoid = H_orthometric + N
    Uses a standard low-degree spherical harmonic approximation of EGM96 geoid.
    """
    lat_r = np.radians(lat)
    lon_r = np.radians(lon)

    # Coarse global geoid harmonic approximation
    n = (
        -30.0 * np.sin(lat_r)
        + 15.0 * np.cos(2 * lat_r)
        - 10.0 * np.sin(2 * lat_r) * np.cos(lon_r)
        + 12.0 * np.cos(lat_r) * np.sin(2 * lon_r)
    )
    return float(n)


def convert_vertical_datum(
    heights: np.ndarray,
    lat: float,
    lon: float,
    src_datum: str = "EGM96",
    dst_datum: str = "WGS84",
) -> np.ndarray:
    """Convert vertical datum between EGM96 (orthometric) and WGS84 (ellipsoidal)."""
    if src_datum.upper() == dst_datum.upper():
        return heights

    n = compute_approx_egm96_undulation(lat, lon)
    if src_datum.upper() == "EGM96" and dst_datum.upper() == "WGS84":
        # Orthometric to ellipsoidal: h = H + N
        return heights + n
    elif src_datum.upper() == "WGS84" and dst_datum.upper() == "EGM96":
        # Ellipsoidal to orthometric: H = h - N
        return heights - n
    return heights


def format_datum_metadata(vertical_crs: str = "EGM96") -> Dict[str, Any]:
    """Return standard vertical datum metadata structure."""
    return {
        "vertical_datum": vertical_crs,
        "geoid_model": "EGM96 (EPSG:5773)",
        "vertical_units": "metres",
    }
