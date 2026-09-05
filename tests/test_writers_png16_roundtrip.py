"""Tests for 16-bit PNG heightmap writer and quantization roundtrip."""

import json

import numpy as np

from backend.depthwizard.io.writers import (
    decode_16bit_heightmap,
    export_job_rasters,
    write_16bit_heightmap,
)


def test_png16_roundtrip_quantization(tmp_path):
    """Assert decoding via the sidecar formula recovers metres to within one quantisation step."""
    png_path = tmp_path / "heightmap_16bit.png"
    json_path = tmp_path / "heightmap.meta.json"

    height, width = 256, 256
    rng = np.random.default_rng(123)
    # Realistic building and terrain heights: 10.0m to 150.0m
    original_heights = rng.uniform(10.0, 150.0, size=(height, width)).astype(np.float32)

    meta = write_16bit_heightmap(
        png_path=png_path,
        json_path=json_path,
        heights=original_heights,
        assumed_gsd_m=0.33,
        is_absolute=True,
        units="metres",
        model_version="dav2s_v1",
        calibration_status="path_a_srtm",
    )

    assert png_path.exists()
    assert json_path.exists()

    # Verify sidecar keys
    required_keys = [
        "is_absolute",
        "units",
        "h_min_raw",
        "h_max_raw",
        "decode_formula",
        "assumed_gsd_m",
        "width",
        "height",
        "model_version",
        "calibration_status",
    ]
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_meta = json.load(f)

    for k in required_keys:
        assert k in loaded_meta, f"Missing key: {k}"

    assert loaded_meta["decode_formula"] == "h_real = h_min_raw + (px/65535)*(h_max_raw-h_min_raw)"
    assert loaded_meta["is_absolute"] is True
    assert loaded_meta["units"] == "metres"
    assert loaded_meta["width"] == width
    assert loaded_meta["height"] == height

    # Decode using sidecar formula
    decoded_heights, _ = decode_16bit_heightmap(png_path, json_path)

    # Theoretical maximum quantization error is 0.5 * step, bounded by 1.0 * step
    step = (meta["h_max_raw"] - meta["h_min_raw"]) / 65535.0
    abs_diff = np.abs(decoded_heights - original_heights)
    max_error = np.max(abs_diff)

    assert max_error <= step + 1e-4, f"Max error {max_error} exceeds quantization step {step}"
    # Elevation range ~140m -> step is ~0.0021m (~2.1mm)
    assert max_error < 0.005, f"Expected sub-centimetre precision, got {max_error}m"


def test_png16_flat_terrain(tmp_path):
    """Assert flat terrain (zero elevation range) does not divide by zero or emit NaN."""
    png_path = tmp_path / "flat.png"
    json_path = tmp_path / "flat.meta.json"

    heights = np.full((128, 128), 42.5, dtype=np.float32)
    meta = write_16bit_heightmap(png_path, json_path, heights)

    assert meta["h_min_raw"] == 42.5
    assert meta["h_max_raw"] == 42.5
    assert meta["elevation_range_m"] == 0.0

    decoded, _ = decode_16bit_heightmap(png_path, json_path)
    assert np.all(np.isfinite(decoded))
    assert np.allclose(decoded, 42.5, atol=1e-3)


def test_png16_negative_and_wide_range(tmp_path):
    """Assert wide elevation range with negative depressions recovers correctly."""
    png_path = tmp_path / "mountain.png"
    json_path = tmp_path / "mountain.meta.json"

    # From Dead Sea depression -50m to high peak 3500m
    heights = np.linspace(-50.0, 3500.0, 100 * 100, dtype=np.float32).reshape((100, 100))
    write_16bit_heightmap(png_path, json_path, heights)

    step = (3500.0 - (-50.0)) / 65535.0  # ~0.054m
    decoded, _ = decode_16bit_heightmap(png_path, json_path)

    abs_diff = np.abs(decoded - heights)
    assert np.max(abs_diff) <= step + 1e-4


def test_png16_nodata_exclusion(tmp_path):
    """Assert nodata values (-9999.0 and NaNs) are excluded from min/max bounds."""
    png_path = tmp_path / "nodata.png"
    json_path = tmp_path / "nodata.meta.json"

    heights = np.full((64, 64), 80.0, dtype=np.float32)
    heights[0, 0] = -9999.0
    heights[0, 1] = np.nan

    meta = write_16bit_heightmap(png_path, json_path, heights, nodata=-9999.0)
    assert meta["h_min_raw"] == 80.0
    assert meta["h_max_raw"] == 80.0


def test_export_job_rasters_non_georeferenced(tmp_path):
    """Assert non-georeferenced scenes export rdsm.tif and relative 16-bit heightmap."""
    rdsm = np.random.rand(64, 64).astype(np.float32)

    artifacts = export_job_rasters(
        output_dir=tmp_path,
        dsm=rdsm,
        is_georeferenced=False,
    )

    assert "rdsm_tif" in artifacts and artifacts["rdsm_tif"].exists()
    assert "heightmap_png" in artifacts and artifacts["heightmap_png"].exists()
    assert "heightmap_json" in artifacts and artifacts["heightmap_json"].exists()

    with open(artifacts["heightmap_json"]) as f:
        meta = json.load(f)
    assert meta["is_absolute"] is False
    assert meta["units"] == "relative"
