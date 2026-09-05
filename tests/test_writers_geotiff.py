"""Tests for GeoTIFF raster writers."""

import subprocess
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from backend.depthwizard.io.writers import export_job_rasters, write_geotiff


def test_write_geotiff_roundtrip(tmp_path):
    """Assert CRS, transform, dtype, nodata, description, and compression are preserved."""
    out_file = tmp_path / "dsm.tif"
    height, width = 512, 512
    rng = np.random.default_rng(42)
    original_data = (rng.normal(loc=120.0, scale=15.0, size=(height, width))).astype(np.float32)
    original_data[0, 0] = -9999.0  # test nodata value preservation

    crs = "EPSG:32618"
    transform = from_origin(323500.0, 4307500.0, 0.33, 0.33)
    desc = "DSM_absolute_metres_EGM96"

    write_geotiff(
        path=out_file,
        data=original_data,
        crs=crs,
        transform=transform,
        nodata=-9999.0,
        description=desc,
        compress="lzw",
        tiled=True,
        blockxsize=512,
        blockysize=512,
    )

    assert out_file.exists()

    with rasterio.open(out_file) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.nodata == -9999.0
        assert src.descriptions[0] == desc
        assert src.crs.to_epsg() == 32618
        assert src.transform == transform
        assert src.profile.get("compress") == "lzw"

        # Check bounds
        bounds = src.bounds
        expected_right = 323500.0 + 512 * 0.33
        expected_bottom = 4307500.0 - 512 * 0.33
        assert np.isclose(bounds.left, 323500.0)
        assert np.isclose(bounds.top, 4307500.0)
        assert np.isclose(bounds.right, expected_right)
        assert np.isclose(bounds.bottom, expected_bottom)

        # Check data
        read_data = src.read(1)
        np.testing.assert_allclose(read_data, original_data, atol=1e-5)


def test_write_ndsm_geotiff(tmp_path):
    """Assert ndsm.tif writes properly with normalized metres description."""
    out_file = tmp_path / "ndsm.tif"
    height, width = 256, 256
    ndsm_data = np.clip(np.random.normal(5.0, 3.0, (height, width)), 0.0, 50.0).astype(np.float32)

    crs = "EPSG:4326"
    transform = from_origin(77.5, 12.9, 0.000003, 0.000003)

    write_geotiff(
        path=out_file,
        data=ndsm_data,
        crs=crs,
        transform=transform,
        nodata=-9999.0,
        description="nDSM_normalised_metres",
        compress="lzw",
        tiled=True,
    )

    with rasterio.open(out_file) as src:
        assert src.crs.to_epsg() == 4326
        assert src.descriptions[0] == "nDSM_normalised_metres"
        np.testing.assert_allclose(src.read(1), ndsm_data, atol=1e-5)


def test_write_rdsm_no_crs(tmp_path):
    """Assert non-georeferenced rdsm.tif writes without CRS error."""
    out_file = tmp_path / "rdsm.tif"
    rdsm_data = np.linspace(0.0, 1.0, 64 * 64, dtype=np.float32).reshape((64, 64))

    write_geotiff(
        path=out_file,
        data=rdsm_data,
        crs=None,
        transform=None,
        description="rDSM_relative",
        tiled=False,
    )

    with rasterio.open(out_file) as src:
        assert src.crs is None
        assert src.dtypes[0] == "float32"
        np.testing.assert_allclose(src.read(1), rdsm_data, atol=1e-5)


def test_export_job_rasters_georeferenced(tmp_path):
    """Assert export_job_rasters creates dsm.tif, ndsm.tif, and 16-bit heightmap."""
    dsm = np.ones((128, 128), dtype=np.float32) * 50.0
    ndsm = np.ones((128, 128), dtype=np.float32) * 10.0
    transform = from_origin(500000, 4000000, 0.33, 0.33)

    artifacts = export_job_rasters(
        output_dir=tmp_path,
        dsm=dsm,
        ndsm=ndsm,
        crs="EPSG:32618",
        transform=transform,
        is_georeferenced=True,
        assumed_gsd_m=0.33,
    )

    assert "dsm_tif" in artifacts and artifacts["dsm_tif"].exists()
    assert "ndsm_tif" in artifacts and artifacts["ndsm_tif"].exists()
    assert "heightmap_png" in artifacts and artifacts["heightmap_png"].exists()
    assert "heightmap_json" in artifacts and artifacts["heightmap_json"].exists()


def test_gdalinfo_cli(tmp_path):
    """Assert gdalinfo reports correct CRS and corner coordinates."""
    out_file = tmp_path / "dsm.tif"
    dsm = np.full((256, 256), 150.0, dtype=np.float32)
    transform = from_origin(300000.0, 4000000.0, 0.33, 0.33)

    write_geotiff(
        path=out_file,
        data=dsm,
        crs="EPSG:32618",
        transform=transform,
    )

    import sys
    bat_path = Path(".venv/Scripts/gdalinfo.bat").resolve()
    if bat_path.exists() and sys.platform == "win32":
        cmd = [str(bat_path), str(out_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    else:
        cmd = [sys.executable, str(Path("scripts/gdalinfo_shim.py").resolve()), str(out_file)]
        res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"gdalinfo failed: {res.stderr}"
    stdout = res.stdout
    assert "32618" in stdout
    assert "300000.000" in stdout
    assert "4000000.000" in stdout
    assert "Corner Coordinates" in stdout
