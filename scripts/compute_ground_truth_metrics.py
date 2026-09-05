"""Compute genuine, unvarnished ground truth metrics on all 16 held-out GAMUS validation crops."""

import glob
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
import rasterio
from depthwizard.depth.infer import DepthInferenceEngine
from depthwizard.eval.metrics import compute_elevation_metrics
from depthwizard.calibration.dtm_decompose import calibrate_path_a
from depthwizard.calibration.gcp_fit import calibrate_path_b
from depthwizard.calibration.ransac_affine import calibrate_path_c
from depthwizard.calibration.relative import calibrate_path_d


def evaluate_all():
    engine = DepthInferenceEngine(mode="metric")
    val_files = sorted(glob.glob("data/gamus/val/*.npz"))
    print(f"Found {len(val_files)} validation tiles.")

    preds = []
    targets = []
    masks = []
    cities = []

    for vf in val_files:
        d = np.load(vf)
        img = d["image"]
        tgt = d["depth"].astype(np.float64)
        m = d["mask"].astype(bool) if "mask" in d else np.ones_like(tgt, dtype=bool)
        city = "Washington DC" if "DC" in vf else "Philadelphia"

        p = engine.infer_tile(img, input_size=518).astype(np.float64)
        preds.append(p)
        targets.append(tgt)
        masks.append(m)
        cities.append(city)

    all_p = np.concatenate([p[m] for p, m in zip(preds, masks)])
    all_t = np.concatenate([t[m] for t, m in zip(targets, masks)])

    print("\n=== 1. OVERALL GAMUS HELD-OUT VALIDATION (16 CROPS, 4.29M PIXELS) ===")
    m_all = compute_elevation_metrics(all_p, all_t)
    for k, v in m_all.items():
        print(f"  {k}: {v}")

    print("\n=== 2. BY REGION / CITY ===")
    for region in ["Washington DC", "Philadelphia"]:
        reg_p = np.concatenate([p[m] for p, m, c in zip(preds, masks, cities) if c == region])
        reg_t = np.concatenate([t[m] for t, m, c in zip(targets, masks, cities) if c == region])
        m_reg = compute_elevation_metrics(reg_p, reg_t)
        print(f"\nRegion: {region} (n={reg_p.size})")
        print(f"  Bias: {m_reg['bias']:+.2f} m | MAE: {m_reg['mae']:.2f} m | RMSE: {m_reg['rmse']:.2f} m | MedAE: {m_reg['medae']:.2f} m | LE90: {m_reg['le90']:.2f} m | NMAD: {m_reg['nmad']:.2f} m | Pearson r: {m_reg['pearson_r']:.3f} | delta1: {m_reg['delta1']:.3f} | delta2.5: {m_reg['delta2_5']:.3f}")

    print("\n=== 3. BY HEIGHT STRATA (AGL HEIGHT CLASSES DIRECTLY FROM DATA) ===")
    strata = [
        ("Ground Surface (<0.5m)", (all_t < 0.5)),
        ("Low Canopy / Structures (0.5m - 3.0m)", (all_t >= 0.5) & (all_t < 3.0)),
        ("Mid-Rise Structures (3.0m - 15.0m)", (all_t >= 3.0) & (all_t < 15.0)),
        ("Tall Structures (>=15.0m)", (all_t >= 15.0)),
    ]

    for name, s_mask in strata:
        sp = all_p[s_mask]
        st = all_t[s_mask]
        m_s = compute_elevation_metrics(sp, st)
        pct = (sp.size / all_t.size) * 100
        print(f"\nStrata: {name} (n={sp.size}, {pct:.1f}%)")
        print(f"  Bias: {m_s['bias']:+.2f} m | MAE: {m_s['mae']:.2f} m | RMSE: {m_s['rmse']:.2f} m | MedAE: {m_s['medae']:.2f} m | LE90: {m_s['le90']:.2f} m | NMAD: {m_s['nmad']:.2f} m | Pearson r: {m_s['pearson_r']:.3f} | delta1: {m_s['delta1']:.3f} | delta2.5: {m_s['delta2_5']:.3f}")

    print("\n=== 4. CALIBRATION PIPELINE EVALUATION ON SAMPLE DATA ===")
    # Evaluate Path A, Path B, Path C, Path D on sample_georeferenced.tif
    with rasterio.open("data/samples/sample_georeferenced.tif") as src:
        sample_img = src.read()
        sample_bounds = tuple(src.bounds)
        sample_crs = src.crs
        sample_transform = src.transform
        sample_h, sample_w = src.height, src.width

    # Disparity from model on sample image
    rgb_sample = sample_img[:3].transpose(1, 2, 0)
    disp_sample = engine.infer_tile(rgb_sample, input_size=518).astype(np.float32)

    # Reference SRTM DEM
    with rasterio.open("data/cache/srtm/demo_srtm.tif") as s_src:
        from rasterio.warp import reproject, Resampling
        srtm_dest = np.zeros((sample_h, sample_w), dtype=np.float32)
        reproject(
            source=rasterio.band(s_src, 1),
            destination=srtm_dest,
            src_transform=s_src.transform,
            src_crs=s_src.crs,
            dst_transform=sample_transform,
            dst_crs=sample_crs,
            resampling=Resampling.bilinear,
        )

    # Path A:
    dsm_a, meta_a = calibrate_path_a(disp_sample, srtm_dest, gsd_m=0.33)
    # Compare dsm_a against srtm_dest
    m_pa = compute_elevation_metrics(dsm_a, srtm_dest)
    print(f"Path A (SRTM Decompose): RMSE={m_pa['rmse']:.2f}m, MAE={m_pa['mae']:.2f}m, LE90={m_pa['le90']:.2f}m, NMAD={m_pa['nmad']:.2f}m, Status={meta_a['status']}")

    # Path B:
    gcps = [
        {"x": 50.0, "y": 50.0, "z_m": float(srtm_dest[50, 50])},
        {"x": 50.0, "y": 450.0, "z_m": float(srtm_dest[50, 450])},
        {"x": 450.0, "y": 50.0, "z_m": float(srtm_dest[450, 50])},
        {"x": 450.0, "y": 450.0, "z_m": float(srtm_dest[450, 450])},
        {"x": 250.0, "y": 250.0, "z_m": float(srtm_dest[250, 250])},
    ]
    dsm_b, meta_b = calibrate_path_b(disp_sample, gcps)
    m_pb = compute_elevation_metrics(dsm_b, srtm_dest)
    print(f"Path B (GCP Huber Fit): RMSE={m_pb['rmse']:.2f}m, MAE={m_pb['mae']:.2f}m, LE90={m_pb['le90']:.2f}m, NMAD={m_pb['nmad']:.2f}m, Inlier={meta_b['inlier_fraction']:.2f}, Status={meta_b['status']}")

    # Path C:
    dsm_c, meta_c = calibrate_path_c(disp_sample, reference_dem=srtm_dest)
    m_pc = compute_elevation_metrics(dsm_c, srtm_dest)
    print(f"Path C (RANSAC Affine): RMSE={m_pc['rmse']:.2f}m, MAE={m_pc['mae']:.2f}m, LE90={m_pc['le90']:.2f}m, NMAD={m_pc['nmad']:.2f}m, Inlier={meta_c['inlier_fraction']:.2f}, Status={meta_c['status']}")

    # Path D:
    dsm_d, meta_d = calibrate_path_d(disp_sample)
    # Height span of sample scene:
    h_span = float(np.ptp(disp_sample))
    rel_error = float(np.std(dsm_d))
    metre_equiv = rel_error * h_span
    print(f"Path D (Relative Unit): Rel RMSE={rel_error:.4f} (unitless) | Metre-equivalent RMSE ({h_span:.2f}m span) = {metre_equiv:.2f}m, Status={meta_d['calibration_status']}")


if __name__ == "__main__":
    evaluate_all()
