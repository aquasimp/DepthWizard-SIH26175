"""Geospatial raster and 16-bit heightmap writers."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
import rasterio
from rasterio.crs import CRS


def write_geotiff(
    path: Union[str, Path],
    data: np.ndarray,
    crs: Any = None,
    transform: Any = None,
    nodata: float = -9999.0,
    description: str = "DSM_absolute_metres_EGM96",
    compress: str = "lzw",
    tiled: bool = True,
    blockxsize: int = 512,
    blockysize: int = 512,
) -> Path:
    """Write float32 GeoTIFF with LZW compression, tiling, and metadata.

    Args:
        path: Output file path.
        data: 2D or (1, H, W) numpy array of elevation values.
        crs: Coordinate Reference System (rasterio CRS, pyproj CRS, or EPSG string).
        transform: Affine transform for georeferencing.
        nodata: Nodata sentinel value (default -9999.0).
        description: Band description string.
        compress: Compression algorithm ('lzw', 'deflate', etc.).
        tiled: Whether to enable TIFF tiling.
        blockxsize: Tile block width (default 512).
        blockysize: Tile block height (default 512).

    Returns:
        Path to written GeoTIFF.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    arr = np.asarray(data)
    if arr.ndim == 3:
        if arr.shape[0] == 1:
            arr = arr[0]
        else:
            raise ValueError(f"Expected 2D array or 1-band array, got shape {arr.shape}")
    elif arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    height, width = arr.shape
    arr_f32 = arr.astype(np.float32)

    profile: Dict[str, Any] = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "nodata": float(nodata),
        "compress": compress,
    }

    if tiled and height >= 16 and width >= 16:
        profile["tiled"] = True
        profile["blockxsize"] = int(blockxsize)
        profile["blockysize"] = int(blockysize)

    if crs is not None:
        if isinstance(crs, str):
            profile["crs"] = CRS.from_user_input(crs)
        else:
            profile["crs"] = crs

    if transform is not None:
        profile["transform"] = transform

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr_f32, 1)
        if description:
            dst.set_band_description(1, description)

    return out_path


def write_16bit_heightmap(
    png_path: Union[str, Path],
    json_path: Union[str, Path],
    heights: np.ndarray,
    metadata: Optional[Dict[str, Any]] = None,
    nodata: float = -9999.0,
    assumed_gsd_m: float = 0.33,
    is_absolute: bool = True,
    units: str = "metres",
    model_version: str = "dav2s_v1",
    calibration_status: str = "calibrated",
) -> Dict[str, Any]:
    """Write 16-bit PNG heightmap normalized to [0, 65535] and sidecar metadata.

    The sidecar metadata records the exact decoding formula:
    h_real = h_min_raw + (px / 65535.0) * (h_max_raw - h_min_raw)

    Args:
        png_path: Target PNG file path.
        json_path: Target JSON sidecar file path.
        heights: 2D numpy array of elevation heights.
        metadata: Optional additional metadata dict to merge.
        nodata: Nodata sentinel to exclude from range calculation.
        assumed_gsd_m: Spatial resolution in metres/pixel.
        is_absolute: Whether elevations are absolute metric or relative.
        units: Unit description string ('metres' or 'relative').
        model_version: Model identifier string.
        calibration_status: Calibration method or status.

    Returns:
        The written metadata dictionary.
    """
    png_file = Path(png_path)
    json_file = Path(json_path)
    png_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.parent.mkdir(parents=True, exist_ok=True)

    arr = np.asarray(heights)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    elif arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    height, width = arr.shape

    # Identify valid metric pixels
    valid_mask = np.isfinite(arr)
    if nodata is not None:
        valid_mask = valid_mask & (~np.isclose(arr, nodata))

    if np.any(valid_mask):
        valid_vals = arr[valid_mask]
        h_min_raw = float(np.min(valid_vals))
        h_max_raw = float(np.max(valid_vals))
    else:
        h_min_raw = 0.0
        h_max_raw = 0.0

    elevation_range = h_max_raw - h_min_raw

    # Normalize to uint16 [0, 65535]
    u16_img = np.zeros((height, width), dtype=np.uint16)
    if elevation_range > 1e-7 and np.any(valid_mask):
        norm = (arr - h_min_raw) / elevation_range
        norm = np.clip(norm, 0.0, 1.0)
        u16_vals = np.round(norm * 65535.0).astype(np.uint16)
        u16_img[valid_mask] = u16_vals[valid_mask]
    elif np.any(valid_mask):
        # Flat scene: assign mid-scale or 0
        u16_img[valid_mask] = 0

    # Write 16-bit PNG using cv2 (supports CV_16U lossless PNG)
    success = cv2.imwrite(str(png_file), u16_img)
    if not success:
        # Fallback to PIL
        from PIL import Image

        pil_img = Image.fromarray(u16_img, mode="I;16")
        pil_img.save(str(png_file))

    sidecar: Dict[str, Any] = {
        "is_absolute": bool(is_absolute),
        "units": str(units),
        "h_min_raw": h_min_raw,
        "h_max_raw": h_max_raw,
        "elevation_range_m": elevation_range,
        "decode_formula": "h_real = h_min_raw + (px/65535)*(h_max_raw-h_min_raw)",
        "assumed_gsd_m": float(assumed_gsd_m),
        "width": int(width),
        "height": int(height),
        "model_version": str(model_version),
        "calibration_status": str(calibration_status),
    }

    if metadata:
        for k, v in metadata.items():
            if k not in sidecar:
                sidecar[k] = v

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2)

    return sidecar


def decode_16bit_heightmap(
    png_path: Union[str, Path],
    json_path: Union[str, Path],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Decode 16-bit PNG heightmap back to metric heights using sidecar metadata.

    Args:
        png_path: Path to 16-bit PNG.
        json_path: Path to sidecar JSON metadata.

    Returns:
        Tuple of (reconstructed_heights_float32, metadata_dict).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Read uint16 image
    px = cv2.imread(str(png_path), cv2.IMREAD_UNCHANGED)
    if px is None:
        from PIL import Image

        px = np.array(Image.open(str(png_path)), dtype=np.uint16)

    h_min = float(meta["h_min_raw"])
    h_max = float(meta["h_max_raw"])
    h_range = h_max - h_min

    h_real = h_min + (px.astype(np.float32) / 65535.0) * h_range
    return h_real.astype(np.float32), meta


def export_job_rasters(
    output_dir: Union[str, Path],
    dsm: np.ndarray,
    ndsm: Optional[np.ndarray] = None,
    crs: Any = None,
    transform: Any = None,
    is_georeferenced: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    assumed_gsd_m: float = 0.33,
    model_version: str = "dav2s_v1",
    calibration_status: str = "calibrated",
) -> Dict[str, Path]:
    """Export all required raster artifacts for a processing job.

    Georeferenced scenes produce:
      - dsm.tif (GeoTIFF float32, EGM96)
      - ndsm.tif (GeoTIFF float32, normalized above-ground height)
      - heightmap_16bit.png + heightmap.meta.json

    Non-georeferenced scenes produce:
      - rdsm.tif (float32 TIFF, no CRS)
      - heightmap_16bit.png + heightmap.meta.json

    Returns:
        Dictionary mapping artifact keys to their file paths.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: Dict[str, Path] = {}

    if is_georeferenced and crs is not None and transform is not None:
        # Write dsm.tif
        dsm_path = out_dir / "dsm.tif"
        write_geotiff(
            path=dsm_path,
            data=dsm,
            crs=crs,
            transform=transform,
            nodata=-9999.0,
            description="DSM_absolute_metres_EGM96",
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
        )
        artifacts["dsm_tif"] = dsm_path

        # Write ndsm.tif if available
        if ndsm is not None:
            ndsm_path = out_dir / "ndsm.tif"
            write_geotiff(
                path=ndsm_path,
                data=ndsm,
                crs=crs,
                transform=transform,
                nodata=-9999.0,
                description="nDSM_normalised_metres",
                compress="lzw",
                tiled=True,
                blockxsize=512,
                blockysize=512,
            )
            artifacts["ndsm_tif"] = ndsm_path
    else:
        # Write rdsm.tif (non-georeferenced float32)
        rdsm_path = out_dir / "rdsm.tif"
        write_geotiff(
            path=rdsm_path,
            data=dsm,
            crs=None,
            transform=None,
            nodata=-9999.0,
            description="rDSM_relative",
            compress="lzw",
            tiled=False,
        )
        artifacts["rdsm_tif"] = rdsm_path

    # Always write 16-bit PNG heightmap + sidecar JSON for the 3D renderer
    png_path = out_dir / "heightmap_16bit.png"
    json_path = out_dir / "heightmap.meta.json"
    write_16bit_heightmap(
        png_path=png_path,
        json_path=json_path,
        heights=dsm,
        metadata=metadata,
        assumed_gsd_m=assumed_gsd_m,
        is_absolute=is_georeferenced,
        units="metres" if is_georeferenced else "relative",
        model_version=model_version,
        calibration_status=calibration_status,
    )
    artifacts["heightmap_png"] = png_path
    artifacts["heightmap_json"] = json_path

    return artifacts
