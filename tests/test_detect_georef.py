"""Tests for georeferencing detection (Phase 3 acceptance check 1)."""

from pathlib import Path

import pytest
from depthwizard.io.detect import CorruptImageError, is_georeferenced


def test_geotiff_with_crs_is_georeferenced(fixtures_dir: Path) -> None:
    """GeoTIFF with valid CRS and transform MUST return True."""
    tiff_path = fixtures_dir / "projected_metres.tif"
    assert is_georeferenced(tiff_path) is True

    geo_path = fixtures_dir / "geographic_degrees.tif"
    assert is_georeferenced(geo_path) is True


def test_tiff_without_crs_is_not_georeferenced(fixtures_dir: Path) -> None:
    """TIFF without CRS (or with identity transform) MUST return False."""
    no_crs_path = fixtures_dir / "no_crs.tif"
    assert is_georeferenced(no_crs_path) is False


def test_standard_formats_not_georeferenced(fixtures_dir: Path) -> None:
    """Standard consumer images (PNG, JPEG) MUST return False without error."""
    png_path = fixtures_dir / "plain.png"
    assert is_georeferenced(png_path) is False

    jpg_path = fixtures_dir / "plain.jpg"
    assert is_georeferenced(jpg_path) is False


def test_corrupt_image_raises_error(fixtures_dir: Path, tmp_path: Path) -> None:
    """Corrupt image or truncated file MUST raise CorruptImageError."""
    corrupt_path = fixtures_dir / "corrupt.tif"
    with pytest.raises(CorruptImageError):
        is_georeferenced(corrupt_path)

    # Empty file
    empty_file = tmp_path / "empty.tif"
    empty_file.touch()
    with pytest.raises(CorruptImageError):
        is_georeferenced(empty_file)

    # Non-existent file
    with pytest.raises(CorruptImageError):
        is_georeferenced(tmp_path / "does_not_exist.tif")
