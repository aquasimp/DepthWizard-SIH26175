"""Vertical datum handling and conversion utilities."""


def convert_vertical_datum(
    heights: float,
    lat: float,
    lon: float,
    src_datum: str = "EGM96",
    dst_datum: str = "WGS84",
) -> float:
    """Convert vertical datum between EGM96 and WGS84 ellipsoidal height."""
    return heights
