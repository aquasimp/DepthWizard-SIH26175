"""Honest Held-Out Re-Evaluation on GAMUS Test Split for DepthWizard v1.1.0.

Evaluates 1,071 held-out test crops across 3 cities (DC, NYC, PHL):
1. Zero-shot Base model (Depth Anything V3 Small relative depth + least-squares metric alignment)
2. v1.0.3 fine-tuned model (models/dav3s_gamus_ft_v1.pth)
3. v1.1.0 fine-tuned model (models/v1.1.0/best.pt)
4. v1.1.0 best-tall model (models/v1.1.0/best_tall.pt)

Computes:
- Bias, MAE, RMSE, MedAE, LE90, NMAD, Pearson r, delta < 1.0m, delta < 2.5m
- Breakdowns:
  - By city: DC, NYC, PHL
  - By height band: [0, 2), [2, 5), [5, 15), [15, 30), [30, inf)
  - By semantic class: 1 (Ground), 2 (Low Veg), 3 (Building), 4 (Water), 5 (Road), 6 (Tree)
- Exports GeoTIFF difference rasters and evaluation plots.
- Saves results to artifacts/v1.1.0/metrics_v1.1.0.json.
"""

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import matplotlib.pyplot as plt
import numpy as np
import torch
from depthwizard.depth.backbone import DepthAnythingV3Small, load_dav3_small
from depthwizard.io.writers import write_geotiff
from torch.utils.data import DataLoader

from training.dataset import GAMUSDataset

CLASS_NAMES = {
    1: "Ground",
    2: "Low Veg",
    3: "Building",
    4: "Water",
    5: "Road",
    6: "Tree",
}

HEIGHT_BANDS = [
    ("0_2m", 0.0, 2.0),
    ("2_5m", 2.0, 5.0),
    ("5_15m", 5.0, 15.0),
    ("15_30m", 15.0, 30.0),
    ("30m_plus", 30.0, float("inf")),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DepthWizard v1.1.0 Held-Out Evaluation")
    parser.add_argument("--batch-size", type=int, default=8, help="Evaluation batch size")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit test samples for quick testing")
    return parser.parse_args()


def compute_comprehensive_metrics(
    errors: np.ndarray,
    preds: np.ndarray,
    targets: np.ndarray,
) -> Dict[str, float]:
    """Compute all evaluation metrics from flattened 1D arrays of errors, preds, and targets."""
    if len(errors) == 0:
        return {
            "count": 0,
            "bias": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "medae": 0.0,
            "le90": 0.0,
            "nmad": 0.0,
            "pearson_r": 0.0,
            "delta_1_0m": 0.0,
            "delta_2_5m": 0.0,
        }

    abs_err = np.abs(errors)
    bias = float(np.mean(errors))
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(errors**2)))
    medae = float(np.median(abs_err))
    le90 = float(np.percentile(abs_err, 90))

    # NMAD = 1.4826 * median(|e - median(e)|)
    nmad = float(1.4826 * np.median(np.abs(errors - np.median(errors))))

    # Pearson r
    std_p = np.std(preds)
    std_t = np.std(targets)
    if std_p > 1e-6 and std_t > 1e-6:
        pearson_r = float(np.corrcoef(preds, targets)[0, 1])
    else:
        pearson_r = 0.0

    delta_1_0m = float(np.mean(abs_err < 1.0))
    delta_2_5m = float(np.mean(abs_err < 2.5))

    return {
        "count": int(len(errors)),
        "bias": round(bias, 4),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "medae": round(medae, 4),
        "le90": round(le90, 4),
        "nmad": round(nmad, 4),
        "pearson_r": round(pearson_r, 4),
        "delta_1_0m": round(delta_1_0m, 4),
        "delta_2_5m": round(delta_2_5m, 4),
    }


def evaluate_model(
    model: DepthAnythingV3Small,
    loader: DataLoader,
    device: torch.device,
    is_base_model: bool = False,
    model_name: str = "",
) -> Dict[str, Any]:
    print(f"\nEvaluating {model_name} on {len(loader.dataset)} test crops...")
    model.eval()

    # Accumulators
    all_errors = []
    all_preds = []
    all_targets = []

    # Per-city
    city_errors = {"DC": [], "NYC": [], "PHL": []}
    city_preds = {"DC": [], "NYC": [], "PHL": []}
    city_targets = {"DC": [], "NYC": [], "PHL": []}

    # Per height band
    band_errors = {name: [] for name, _, _ in HEIGHT_BANDS}
    band_preds = {name: [] for name, _, _ in HEIGHT_BANDS}
    band_targets = {name: [] for name, _, _ in HEIGHT_BANDS}

    # Per class (1..6)
    class_errors = {c: [] for c in range(1, 7)}
    class_preds = {c: [] for c in range(1, 7)}
    class_targets = {c: [] for c in range(1, 7)}

    t0 = time.perf_counter()
    with torch.no_grad():
        for batch_idx, batch in enumerate(loader):
            imgs = batch["image"].to(device, non_blocking=True)
            tgts = batch["depth"].to(device, non_blocking=True)
            msks = batch["mask"].to(device, non_blocking=True)
            classes = batch["class"].to(device, non_blocking=True)
            cities = batch.get("city", ["UNKNOWN"] * len(imgs))

            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                feats = model.pretrained(imgs)
                preds = model.depth_head(feats, 37, 37)

            # Move to CPU numpy for precision
            preds_np = preds.squeeze(1).cpu().numpy()
            tgts_np = tgts.squeeze(1).cpu().numpy()
            msks_np = msks.squeeze(1).cpu().numpy()
            cls_np = classes.squeeze(1).cpu().numpy()

            for i in range(len(imgs)):
                p = preds_np[i]
                t = tgts_np[i]
                m = msks_np[i] & np.isfinite(p) & np.isfinite(t) & (t >= 0.0)
                c_map = cls_np[i]
                city = cities[i] if i < len(cities) else "UNKNOWN"

                if not m.any():
                    continue

                p_val = p[m]
                t_val = t[m]
                c_val = c_map[m]

                # If evaluating raw relative base model, apply affine least-squares alignment per crop
                if is_base_model:
                    A = np.vstack([p_val, np.ones_like(p_val)]).T
                    try:
                        s, offset = np.linalg.lstsq(A, t_val, rcond=None)[0]
                        p_val = s * p_val + offset
                    except Exception:
                        pass

                err_val = p_val - t_val

                # Subsample to keep in RAM if needed, but for 1071 crops:
                # 1071 * 260k pixels = ~280M pixels. We can subsample 1:10 for memory efficiency
                # or accumulate histograms/moments. Let's subsample 1 every 8 pixels (stride 8)
                sub_mask = np.arange(len(err_val)) % 8 == 0
                err_sub = err_val[sub_mask]
                p_sub = p_val[sub_mask]
                t_sub = t_val[sub_mask]
                c_sub = c_val[sub_mask]

                all_errors.append(err_sub)
                all_preds.append(p_sub)
                all_targets.append(t_sub)

                if city in city_errors:
                    city_errors[city].append(err_sub)
                    city_preds[city].append(p_sub)
                    city_targets[city].append(t_sub)

                for b_name, b_min, b_max in HEIGHT_BANDS:
                    b_idx = (t_sub >= b_min) & (t_sub < b_max)
                    if b_idx.any():
                        band_errors[b_name].append(err_sub[b_idx])
                        band_preds[b_name].append(p_sub[b_idx])
                        band_targets[b_name].append(t_sub[b_idx])

                for cls_id in range(1, 7):
                    c_idx = (c_sub == cls_id)
                    if c_idx.any():
                        class_errors[cls_id].append(err_sub[c_idx])
                        class_preds[cls_id].append(p_sub[c_idx])
                        class_targets[cls_id].append(t_sub[c_idx])

            if (batch_idx + 1) % 25 == 0 or (batch_idx + 1) == len(loader):
                print(f"  Batch {batch_idx + 1}/{len(loader)} evaluated...")

    dt = time.perf_counter() - t0
    print(f"Evaluation of {model_name} completed in {dt:.1f} s")

    # Flatten arrays
    flat_errors = np.concatenate(all_errors) if all_errors else np.array([])
    flat_preds = np.concatenate(all_preds) if all_preds else np.array([])
    flat_targets = np.concatenate(all_targets) if all_targets else np.array([])

    overall_metrics = compute_comprehensive_metrics(flat_errors, flat_preds, flat_targets)

    # City metrics
    by_city = {}
    for city in ["DC", "NYC", "PHL"]:
        c_e = np.concatenate(city_errors[city]) if city_errors[city] else np.array([])
        c_p = np.concatenate(city_preds[city]) if city_preds[city] else np.array([])
        c_t = np.concatenate(city_targets[city]) if city_targets[city] else np.array([])
        by_city[city] = compute_comprehensive_metrics(c_e, c_p, c_t)

    # Height band metrics
    by_height = {}
    for b_name, _, _ in HEIGHT_BANDS:
        b_e = np.concatenate(band_errors[b_name]) if band_errors[b_name] else np.array([])
        b_p = np.concatenate(band_preds[b_name]) if band_preds[b_name] else np.array([])
        b_t = np.concatenate(band_targets[b_name]) if band_targets[b_name] else np.array([])
        by_height[b_name] = compute_comprehensive_metrics(b_e, b_p, b_t)

    # Semantic class metrics
    by_class = {}
    for cls_id in range(1, 7):
        name = f"{cls_id}_{CLASS_NAMES[cls_id]}"
        cl_e = np.concatenate(class_errors[cls_id]) if class_errors[cls_id] else np.array([])
        cl_p = np.concatenate(class_preds[cls_id]) if class_preds[cls_id] else np.array([])
        cl_t = np.concatenate(class_targets[cls_id]) if class_targets[cls_id] else np.array([])
        by_class[name] = compute_comprehensive_metrics(cl_e, cl_p, cl_t)

    return {
        "model_name": model_name,
        "evaluation_seconds": round(dt, 2),
        "overall": overall_metrics,
        "by_city": by_city,
        "by_height_band": by_height,
        "by_semantic_class": by_class,
        "raw_sample_arrays": {
            "errors": flat_errors[:50000].tolist(),  # Keep small sample for CDF plotting
            "preds": flat_preds[:50000].tolist(),
            "targets": flat_targets[:50000].tolist(),
        },
    }


def generate_evaluation_plots(results: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Error CDF Comparison Plot
    plt.figure(figsize=(9, 5), dpi=150)
    for model_key, res in results.items():
        errs = np.abs(np.array(res["raw_sample_arrays"]["errors"]))
        if len(errs) > 0:
            sorted_errs = np.sort(errs)
            cdf = np.linspace(0, 1, len(sorted_errs))
            plt.plot(sorted_errs, cdf, label=f"{res['model_name']} (LE90={res['overall']['le90']}m)")

    plt.xlim(0, 15)
    plt.ylim(0, 1)
    plt.xlabel("Absolute Error |y_pred - y_true| (metres)")
    plt.ylabel("Cumulative Probability (CDF)")
    plt.title("Error CDF Comparison on Held-Out GAMUS Test Split")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="lower right")
    plt.tight_layout()
    cdf_path = output_dir / "evaluation_error_cdf.png"
    plt.savefig(str(cdf_path))
    plt.close()
    print(f"Saved CDF plot to: {cdf_path}")

    # 2. RMSE by Height Band Bar Chart
    bands = [b[0] for b in HEIGHT_BANDS]
    band_labels = ["0-2m (Flat)", "2-5m (Low)", "5-15m (Med)", "15-30m (Tall)", ">=30m (High-rise)"]
    x = np.arange(len(bands))
    width = 0.25

    plt.figure(figsize=(11, 5.5), dpi=150)
    idx = 0
    colors = ["#94a3b8", "#f59e0b", "#10b981", "#6366f1"]
    for model_key, res in results.items():
        rmses = [res["by_height_band"][b]["rmse"] for b in bands]
        offset = (idx - len(results) / 2 + 0.5) * width
        plt.bar(x + offset, rmses, width, label=res["model_name"], color=colors[idx % len(colors)], alpha=0.85)
        idx += 1

    plt.xticks(x, band_labels)
    plt.xlabel("Height Band")
    plt.ylabel("RMSE (metres)")
    plt.title("Elevation RMSE Across Height Bands (Did the Tall-Structure Gap Close?)")
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    bar_path = output_dir / "evaluation_rmse_by_height.png"
    plt.savefig(str(bar_path))
    plt.close()
    print(f"Saved height band plot to: {bar_path}")

    # 3. Tall Structure (>=15m) Scatter / Residual Plot
    fig, axes = plt.subplots(1, len(results), figsize=(5 * len(results), 4.5), dpi=150, sharey=True)
    if len(results) == 1:
        axes = [axes]

    for ax, (model_key, res) in zip(axes, results.items()):
        p = np.array(res["raw_sample_arrays"]["preds"])
        t = np.array(res["raw_sample_arrays"]["targets"])
        tall_idx = t >= 15.0
        p_tall = p[tall_idx]
        t_tall = t[tall_idx]
        if len(p_tall) > 2000:
            sample_sub = np.random.choice(len(p_tall), 2000, replace=False)
            p_tall = p_tall[sample_sub]
            t_tall = t_tall[sample_sub]

        ax.scatter(t_tall, p_tall, alpha=0.3, s=8, color="#2563eb")
        ax.plot([15, 60], [15, 60], "r--", label="Ideal 1:1")
        ax.set_xlabel("Ground Truth nDSM (m)")
        ax.set_ylabel("Predicted Height (m)")
        ax.set_title(f"{res['model_name']}\nTall RMSE: {res['by_height_band']['15_30m']['rmse']}m")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.set_xlim(15, 60)
        ax.set_ylim(0, 70)
        ax.legend(loc="upper left")

    plt.tight_layout()
    scatter_path = output_dir / "evaluation_tall_scatter.png"
    plt.savefig(str(scatter_path))
    plt.close()
    print(f"Saved tall scatter plot to: {scatter_path}")


def export_sample_geotiffs(
    model: DepthAnythingV3Small,
    dataset: GAMUSDataset,
    device: torch.device,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model.eval()

    # Find 3 sample crops from test split: 1 DC, 1 NYC, 1 PHL with tall buildings
    sample_indices = []
    found_cities = set()
    for idx in range(len(dataset)):
        row = dataset.rows[idx]
        city = row.get("city", "")
        tf = float(row.get("band_15_30", 0.0)) + float(row.get("band_30_inf", 0.0))
        if city not in found_cities and tf >= 0.10:
            sample_indices.append(idx)
            found_cities.add(city)
        if len(found_cities) >= 3:
            break

    print(f"Exporting GeoTIFF difference rasters for {len(sample_indices)} test tiles...")
    with torch.no_grad():
        for idx in sample_indices:
            sample = dataset[idx]
            img = sample["image"].unsqueeze(0).to(device)
            tgt = sample["depth"].squeeze().numpy()
            msk = sample["mask"].squeeze().numpy()
            row = dataset.rows[idx]
            crop_id = row.get("crop_id", f"crop_{idx}")

            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                feats = model.pretrained(img)
                pred = model.depth_head(feats, 37, 37).squeeze().cpu().numpy()

            diff = np.where(msk, pred - tgt, -9999.0).astype(np.float32)
            pred_out = np.where(msk, pred, -9999.0).astype(np.float32)
            tgt_out = np.where(msk, tgt, -9999.0).astype(np.float32)

            write_geotiff(output_dir / f"{crop_id}_pred.tif", pred_out, nodata=-9999.0, description="Predicted_nDSM_m")
            write_geotiff(output_dir / f"{crop_id}_gt.tif", tgt_out, nodata=-9999.0, description="GroundTruth_nDSM_m")
            write_geotiff(output_dir / f"{crop_id}_diff.tif", diff, nodata=-9999.0, description="Error_pred_minus_gt_m")

    print(f"Exported sample GeoTIFF rasters to: {output_dir}")


def run_evaluation(args: argparse.Namespace) -> Dict[str, Any]:
    manifest_path = repo_root / "data" / "gamus" / "manifest.csv"
    assert manifest_path.exists(), f"Manifest not found at {manifest_path}"

    test_ds = GAMUSDataset(manifest_path=manifest_path, split="test", crop_size=518, augment=False)
    print(f"Loaded held-out test split: {len(test_ds)} crops")
    if args.max_samples and args.max_samples < len(test_ds):
        test_ds.rows = test_ds.rows[:args.max_samples]
        test_ds.samples = test_ds.rows
        print(f"Subsampled to {len(test_ds)} crops for evaluation")

    test_loader = DataLoader(

        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(args.device == "cuda"),
    )

    device = torch.device(args.device)

    # 1. Base Model (Zero-Shot Relative + Affine Alignment)
    base_path = (
        repo_root / "models" / "depth_anything_v3_vits.pth"
        if (repo_root / "models" / "depth_anything_v3_vits.pth").exists()
        else repo_root / "models" / "depth_anything_v2_vits.pth"
    )
    base_model = load_dav3_small(base_path, device=str(device))
    base_results = evaluate_model(base_model, test_loader, device, is_base_model=True, model_name="Zero-Shot Base (DAV3-S)")

    # 2. v1.0.3 Model
    v103_path = (
        repo_root / "models" / "dav3s_gamus_ft_v1.pth"
        if (repo_root / "models" / "dav3s_gamus_ft_v1.pth").exists()
        else repo_root / "models" / "dav2s_gamus_ft_v1.pth"
    )
    v103_model = load_dav3_small(v103_path, device=str(device))
    v103_results = evaluate_model(v103_model, test_loader, device, is_base_model=False, model_name="v1.0.3 Checkpoint")

    # 3. v1.1.0 Model (best.pt)
    v110_path = repo_root / "models" / "v1.1.0" / "best.pt"
    if not v110_path.exists():
        v110_path = repo_root / "models" / "v1.1.0" / "last.pt"
    v110_model = load_dav3_small(v110_path, device=str(device))
    v110_results = evaluate_model(v110_model, test_loader, device, is_base_model=False, model_name="v1.1.0 Best Val Checkpoint")

    # 4. v1.1.0 Best Tall Model (if present)
    v110_tall_path = repo_root / "models" / "v1.1.0" / "best_tall.pt"
    results_dict = {
        "base_zero_shot": base_results,
        "v1_0_3": v103_results,
        "v1_1_0_best": v110_results,
    }

    if v110_tall_path.exists() and v110_tall_path.stat().st_size > 0:
        v110_tall_model = load_dav3_small(v110_tall_path, device=str(device))
        v110_tall_results = evaluate_model(v110_tall_model, test_loader, device, is_base_model=False, model_name="v1.1.0 Best Tall Checkpoint")
        results_dict["v1_1_0_best_tall"] = v110_tall_results

    # Generate plots
    artifacts_dir = repo_root / "artifacts" / "v1.1.0"
    generate_evaluation_plots(results_dict, artifacts_dir)

    # Export sample GeoTIFF rasters
    rasters_dir = artifacts_dir / "rasters"
    export_sample_geotiffs(v110_model, test_ds, device, rasters_dir)

    # Prepare output dictionary without raw arrays
    clean_output = {
        "evaluation_split": "test",
        "total_test_crops": len(test_ds),
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "models": {
            k: {
                "model_name": v["model_name"],
                "evaluation_seconds": v["evaluation_seconds"],
                "overall": v["overall"],
                "by_city": v["by_city"],
                "by_height_band": v["by_height_band"],
                "by_semantic_class": v["by_semantic_class"],
            }
            for k, v in results_dict.items()
        },
    }

    out_json = artifacts_dir / "metrics_v1.1.0.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(clean_output, f, indent=2)
    print(f"\nSaved held-out evaluation metrics to: {out_json}")

    return clean_output


if __name__ == "__main__":
    args = parse_args()
    run_evaluation(args)
