"""Tests for offline cached SRTM fetch and Path A calibration (Acceptance check 4)."""

from pathlib import Path

import numpy as np
import rasterio
from depthwizard.calibration.dtm_decompose import calibrate_path_a
from depthwizard.calibration.srtm import fetch_srtm_dem


def test_cached_srtm_tile_loads_offline() -> None:
    """Acceptance check 4: Path A runs offline against pre-cached SRTM tile."""
    repo_root = Path(__file__).resolve().parent.parent
    sample_tif = repo_root / "data" / "samples" / "sample_georeferenced.tif"
    cache_dir = repo_root / "data" / "cache" / "srtm"

    assert (cache_dir / "demo_srtm.tif").exists(), "Pre-cached demo SRTM tile must exist."

    with rasterio.open(str(sample_tif)) as src:
        bounds = tuple(src.bounds)
        target_shape = (src.height, src.width)
        target_crs = src.crs
        target_transform = src.transform

    # Fetch SRTM offline with no API key and no internet access
    srtm_grid = fetch_srtm_dem(
        bounds=bounds,
        target_shape=target_shape,
        target_crs=target_crs,
        target_transform=target_transform,
        cache_dir=cache_dir,
        api_key="",
    )

    assert srtm_grid.shape == (512, 512)
    assert srtm_grid.dtype == np.float32
    assert np.all(np.isfinite(srtm_grid))
    # Values should be realistic terrain elevation in metres
    assert 5.0 <= float(np.mean(srtm_grid)) <= 100.0

    # Run Path A calibration with this cached SRTM grid
    dummy_ndsm = np.zeros((512, 512), dtype=np.float32)
    # 5% building coverage
    dummy_ndsm[100:200, 100:200] = 15.0
    calibrated_dsm, meta = calibrate_path_a(
        ndsm=dummy_ndsm,
        srtm_dem=srtm_grid,
        gsd_m=0.33,
    )

    assert meta["calibration_path"] == "PATH_A_SRTM_DECOMPOSE"
    assert meta["is_absolute"] is True
    assert meta["status"] == "CALIBRATED"
    assert calibrated_dsm.shape == (512, 512)
