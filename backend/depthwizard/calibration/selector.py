"""Calibration path selector."""



def select_calibration_path(
    is_georef: bool,
    has_gcps: bool,
    has_srtm: bool,
) -> str:
    """Select appropriate calibration path (A, B, C, or D)."""
    if has_gcps:
        return "PATH_B"
    if is_georef and has_srtm:
        return "PATH_A"
    if is_georef and not has_srtm:
        return "PATH_C"
    return "PATH_D"
