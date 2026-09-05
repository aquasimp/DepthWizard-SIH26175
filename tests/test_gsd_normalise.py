"""Tests for GSD calculation, canonical resampling, and image reading (Phase 3)."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from depthwizard.io.detect import CorruptImageError
from depthwizard.io.gsd import compute_gsd, resample_to_canonical_gsd
from depthwizard.io.readers import (
    ImageDimensionExceededError,
    NonNorthUpError,
    read_image_rgb,
)


def test_gsd_calculation_projected(fixtures_dir: Path) -> None:
    """Projected CRS (metres) GSD calculation."""
    with rasterio.open(str(fixtures_dir / "projected_metres.tif")) as src:
        gsd = compute_gsd(src.transform, src.crs, src.height, src.width)
        # Transform was created with 1.0m pixel width/height
        assert pytest.approx(gsd, rel=1e-3) == 1.0


def test_gsd_calculation_geographic(fixtures_dir: Path) -> None:
    """Geographic CRS (degrees) GSD calculation produces plausible metre value."""
    with rasterio.open(str(fixtures_dir / "geographic_degrees.tif")) as src:
        gsd = compute_gsd(src.transform, src.crs, src.height, src.width)
        # At latitude ~28.6 deg: 0.00001 deg lon is ~0.978 m, 0.00001 deg lat is ~1.113 m
        # Mean GSD should be ~1.045 m
        assert 0.5 < gsd < 2.0
        assert pytest.approx(gsd, rel=0.1) == 1.05


def test_gsd_normalisation_resample_factor() -> None:
    """1.0 m/px image resampled to 0.33 m/px canonical GSD yields resample_factor ~3.03."""
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    current_gsd = 1.0
    target_gsd = 0.33

    resampled, meta = resample_to_canonical_gsd(dummy_img, current_gsd, target_gsd)

    # resample_factor = 1.0 / 0.33 = 3.0303...
    assert pytest.approx(meta["resample_factor"], rel=1e-2) == 3.03
    assert meta["target_gsd"] == 0.33
    assert meta["original_gsd"] == 1.0

    # Output dimensions should be ~303 x ~303
    expected_dim = int(round(100 * (1.0 / 0.33)))
    assert resampled.shape == (expected_dim, expected_dim, 3)


def test_rotated_transform_raises_non_north_up(fixtures_dir: Path) -> None:
    """Image with rotated/sheared transform MUST raise NonNorthUpError."""
    rot_path = fixtures_dir / "rotated.tif"
    with pytest.raises(NonNorthUpError):
        read_image_rgb(rot_path)


def test_16bit_tiff_normalized_no_clipping(fixtures_dir: Path) -> None:
    """16-bit TIFF must normalize to uint8 without clipping artifacts."""
    u16_path = fixtures_dir / "uint16.tif"
    rgb, meta = read_image_rgb(u16_path)

    assert rgb.dtype == np.uint8
    assert rgb.shape == (100, 100, 3)
    # The fixture had values up to ~59925, so max uint8 value should be around 234, not all saturated at 255
    assert 200 <= int(rgb.max()) <= 245
    # Should have a rich distribution, not a single clipped value
    assert int(rgb.min()) == 0


def test_single_band_tiff_replicated_to_3band(fixtures_dir: Path) -> None:
    """Single-band grayscale TIFF must yield shape (H, W, 3) uint8."""
    gray_path = fixtures_dir / "single_band.tif"
    rgb, meta = read_image_rgb(gray_path)

    assert rgb.dtype == np.uint8
    assert rgb.shape == (100, 100, 3)
    # All three channels should be identical
    np.testing.assert_array_equal(rgb[:, :, 0], rgb[:, :, 1])
    np.testing.assert_array_equal(rgb[:, :, 0], rgb[:, :, 2])


def test_image_dimension_exceeded(fixtures_dir: Path) -> None:
    """Images exceeding max_upload_px must raise ImageDimensionExceededError."""
    proj_path = fixtures_dir / "projected_metres.tif"
    # Set max_upload_px lower than fixture size (100)
    with pytest.raises(ImageDimensionExceededError):
        read_image_rgb(proj_path, max_upload_px=50)


def test_corrupt_file_raises_in_reader(fixtures_dir: Path) -> None:
    """Corrupt image must raise CorruptImageError in read_image_rgb."""
    corrupt_path = fixtures_dir / "corrupt.tif"
    with pytest.raises(CorruptImageError):
        read_image_rgb(corrupt_path)
