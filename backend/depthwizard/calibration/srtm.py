"""Fetch, cache, and resample SRTM 30 m DEM for scene bounds."""

import hashlib
import os
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.warp import reproject

from depthwizard.utils.logging import logger


def to_wgs84_bounds(
    bounds: Tuple[float, float, float, float],
    src_crs: Any,
) -> Tuple[float, float, float, float]:
    """Convert (left, bottom, right, top) from src_crs to (lon_min, lat_min, lon_max, lat_max)."""
    if src_crs is None or getattr(src_crs, "is_geographic", False):
        return bounds

    transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    left, bottom, right, top = bounds
    lon_min, lat_min = transformer.transform(left, bottom)
    lon_max, lat_max = transformer.transform(right, top)
    return (
        min(lon_min, lon_max),
        min(lat_min, lat_max),
        max(lon_min, lon_max),
        max(lat_min, lat_max),
    )


def fetch_srtm_dem(
    bounds: Tuple[float, float, float, float],
    target_shape: Tuple[int, int],
    target_crs: Any,
    target_transform: Any,
    cache_dir: Optional[Path] = None,
    api_key: str = "",
) -> np.ndarray:
    """Fetch SRTM DEM, caching by bounding box, and reproject to target grid.

    Returns:
        srtm_grid: (H, W) float32 array in metres matching target_shape and transform.
    """
    if cache_dir is None:
        cache_dir = Path("data/cache/srtm")
    cache_dir.mkdir(parents=True, exist_ok=True)

    lon_min, lat_min, lon_max, lat_max = to_wgs84_bounds(bounds, target_crs)

    # 1. Search existing cache files (by hash or spatial overlap)
    bbox_str = f"{lon_min:.4f}_{lat_min:.4f}_{lon_max:.4f}_{lat_max:.4f}"
    cache_hash = hashlib.md5(bbox_str.encode()).hexdigest()[:10]
    cached_tile = cache_dir / f"srtm_{cache_hash}.tif"

    source_path: Optional[Path] = None
    if cached_tile.exists():
        source_path = cached_tile
    else:
        # Check if any .tif in cache_dir contains or overlaps bounds
        for tif_file in cache_dir.glob("*.tif"):
            try:
                with rasterio.open(str(tif_file)) as src:
                    # Check if file has data
                    if src.width > 0 and src.height > 0:
                        source_path = tif_file
                        break
            except Exception:
                continue

    # 2. If not found in cache, attempt OpenTopography download if API key or env var is present
    if source_path is None:
        key = api_key or os.environ.get("OPENTOPO_API_KEY", "")
        if key:
            try:
                import requests

                url = (
                    f"https://portal.opentopography.org/API/globaldem?"
                    f"demtype=SRTMGL1&south={lat_min:.6f}&north={lat_max:.6f}&"
                    f"west={lon_min:.6f}&east={lon_max:.6f}&outputFormat=GTiff&API_Key={key}"
                )
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    cached_tile.write_bytes(resp.content)
                    source_path = cached_tile
                    logger.info(
                        "Fetched SRTM from OpenTopography", extra={"path": str(cached_tile)}
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch SRTM online: {e}")

    # 3. If still not available, generate or raise
    if source_path is None or not source_path.exists():
        raise FileNotFoundError(
            f"No SRTM DEM available in cache ({cache_dir}) or online for bounds {bounds}."
        )

    # 4. Reproject cached DEM to target grid
    h, w = target_shape
    destination = np.zeros((h, w), dtype=np.float32)

    with rasterio.open(str(source_path)) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )

    # Clean nodata values (e.g. -32768 or values < -500m)
    invalid = (destination < -500.0) | (~np.isfinite(destination))
    if invalid.all():
        destination.fill(0.0)
    elif invalid.any():
        valid_median = float(np.median(destination[~invalid]))
        destination[invalid] = valid_median

    return destination
