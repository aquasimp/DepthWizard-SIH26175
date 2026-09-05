"""Generate signed difference GeoTIFF against genuine ground truth reference and compute reconstructed RMSE."""

import math
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
import rasterio
from rasterio.transform import from_origin
from depthwizard.depth.infer import DepthInferenceEngine
from depthwizard.io.writers import write_geotiff


def generate_difference_raster(
    val_npz_path: str = "data/gamus/val/val_DC_02_26_crop0.npz",
    output_tif: str = "outputs/evaluation/signed_difference_ndsm.tif",
) -> None:
    print(f"Loading genuine reference from {val_npz_path}...")
    data = np.load(val_npz_path)
    rgb = data["image"]  # (518, 518, 3)
    target = data["depth"].astype(np.float32)  # (518, 518)
    mask = data["mask"].astype(bool) if "mask" in data else np.ones_like(target, dtype=bool)

    engine = DepthInferenceEngine(mode="metric")
    pred = engine.infer_tile(rgb, input_size=518).astype(np.float32)

    # Compute signed difference: residual = pred - target
    diff = np.full_like(target, fill_value=-9999.0, dtype=np.float32)
    valid_mask = mask & np.isfinite(pred) & np.isfinite(target) & (target > -1000)
    diff[valid_mask] = pred[valid_mask] - target[valid_mask]

    # Georeference: use DC UTM 18N (EPSG:32618) with 0.33m GSD
    crs = "EPSG:32618"
    transform = from_origin(323500.0, 4307500.0, 0.33, 0.33)

    out_path = Path(output_tif)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    write_geotiff(
        path=out_path,
        data=diff,
        crs=crs,
        transform=transform,
        nodata=-9999.0,
        description="Signed_Difference_Pred_Minus_GT_metres",
    )
    print(f"Exported signed difference GeoTIFF to {out_path}")

    # Read back and compute statistics
    with rasterio.open(out_path) as src:
        band = src.read(1)
        valid = band != src.nodata
        valid_diff = band[valid].astype(np.float64)

    stat_mean = float(np.mean(valid_diff))
    stat_std = float(np.std(valid_diff))
    reconstructed_rmse = math.sqrt(stat_mean**2 + stat_std**2)
    direct_rmse = float(np.sqrt(np.mean(valid_diff**2)))

    print("\n=== Signed Difference Raster Statistics ===")
    print(f"Valid pixels: {valid_diff.size}")
    print(f"STATISTICS_MEAN: {stat_mean:.4f}")
    print(f"STATISTICS_STDDEV: {stat_std:.4f}")
    print(f"Reconstructed RMSE = sqrt(mean^2 + std^2): {reconstructed_rmse:.4f} m")
    print(f"Direct RMSE = sqrt(mean(diff^2)): {direct_rmse:.4f} m")
    print(f"Match between reconstructed and direct RMSE: {math.isclose(reconstructed_rmse, direct_rmse, rel_tol=1e-5)}")


if __name__ == "__main__":
    generate_difference_raster()
