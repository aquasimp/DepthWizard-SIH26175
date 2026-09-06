"""DepthWizard v1.1.0 GAMUS Data Preparation & Stratification Pipeline.

Implements Phase 3 requirements:
- City filtering: DC, NYC, PHL only (OMA and JAX strictly excluded).
- Split integrity: official train/val/test boundaries strictly preserved.
- Two-wave train stratification: Wave 1 probe -> Wave 2 tall-structure enrichment.
- Val/Test: strictly uniform, unstratified, natural distribution.
- 518x518 crop extraction (offsets 0, 506) with zero height resampling.
- Quality control: drop >30% NaN, drop height < -1.0m, quarantine p99.9 > city ceiling, drop all-class-0.
- Output: crop .npz files, manifest CSV, data_qc_report.json, dataset_stats_v1.1.0.json, height_distribution.png.
"""

import csv
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import h5py
import matplotlib.pyplot as plt
import numpy as np
from huggingface_hub import hf_hub_download

# Disable HF symlinks warning on Windows and configure cache
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = str(Path(__file__).resolve().parent.parent / "data" / "cache" / "huggingface")

REPO_ID = "earthflow/GAMUS"
SEED = 1337
RNG = np.random.RandomState(SEED)

CITY_CEILINGS = {
    "DC": 200.0,
    "PHL": 350.0,
    "NYC": 550.0,
}

TARGET_QUOTAS = {
    "train": {"DC": 350, "NYC": 350, "PHL": 350},  # total 1050
    "val": {"DC": 75, "NYC": 0, "PHL": 75},         # total 150 (NYC has 0 in official val)
    "test": {"DC": 100, "NYC": 100, "PHL": 100},   # total 300
}


def load_hf_triplets(hf_file_list_path: Path) -> Dict[str, Dict[str, List[Tuple[str, str, str, str]]]]:
    """Parse hf_file_list.txt and assemble complete triplets grouped by split and city.

    Returns grouped[split][city] = [(base_clean, img_rel_path, agl_rel_path, cls_rel_path)]
    """
    with open(hf_file_list_path, "r", encoding="utf-8") as f:
        files = set(line.strip() for line in f if line.strip())

    grouped = defaultdict(lambda: defaultdict(list))
    for f in sorted(list(files)):
        if f.startswith("images/"):
            parts = f.split("/")
            if len(parts) == 3:
                split = parts[1]
                fname = parts[2]
                base_prefix = fname[:-6]  # e.g. "DC_01_25_" or "NYC_00735_"
                base_clean = base_prefix[:-1]  # "DC_01_25" or "NYC_00735"
                agl_path = f"heights/{split}/{base_prefix}AGL.h5"
                cls_path = f"classes/{split}/{base_prefix}CLS.h5"

                city = base_clean.split("_")[0]
                if city in ["OMA", "JAX"]:
                    raise ValueError(f"CRITICAL ERROR: OMA or JAX file detected in candidate pool: {f}")
                if city in ["DC", "NYC", "PHL"]:
                    if agl_path in files and cls_path in files:
                        grouped[split][city].append((base_clean, f, agl_path, cls_path))

    return grouped



def download_file(hf_rel_path: str, raw_dir: Path, retries: int = 3) -> Path:
    """Download a single file from HF with retries, placing in raw_dir."""
    target_path = raw_dir / hf_rel_path
    if target_path.exists() and target_path.stat().st_size > 0:
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        try:
            downloaded = hf_hub_download(
                repo_id=REPO_ID,
                filename=hf_rel_path,
                repo_type="dataset",
                local_dir=str(raw_dir),
            )
            return Path(downloaded)
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to download {hf_rel_path} after {retries} attempts: {e}")
            time.sleep(1.0 + attempt * 2.0)
    return target_path


def compute_tile_tall_fraction(agl_path: Path) -> Tuple[float, float, float]:
    """Compute (tall_fraction_ge_15m, mean_height, p99_height) from an AGL HDF5 file."""
    with h5py.File(agl_path, "r") as f:
        arr = f["image"][()]
    valid = np.isfinite(arr) & (arr >= 0.0)
    valid_count = int(np.sum(valid))
    if valid_count == 0:
        return 0.0, 0.0, 0.0
    tall_count = int(np.sum(valid & (arr >= 15.0)))
    tall_frac = tall_count / valid_count
    valid_vals = arr[valid]
    return float(tall_frac), float(np.mean(valid_vals)), float(np.percentile(valid_vals, 99))


def wave1_and_wave2_train_selection(
    train_candidates: Dict[str, List[Tuple[str, str, str, str]]],
    quotas: Dict[str, int],
    raw_dir: Path,
    num_workers: int = 16,
) -> Tuple[List[Tuple[str, str, str, str]], Dict]:
    """Execute Wave 1 probe and Wave 2 tall-structure stratified train selection."""
    print("\n--- Starting Phase 3.4: Wave 1 Probe of Candidate Train Pool ---")
    wave1_stats = {}
    selected_train_tiles: List[Tuple[str, str, str, str]] = []

    for city in ["DC", "NYC", "PHL"]:
        city_candidates = list(train_candidates[city])
        target_n = quotas[city]
        RNG.shuffle(city_candidates)

        # Wave 1: Probe a 20% random sample (or up to 120 candidates)
        probe_size = max(50, min(150, int(len(city_candidates) * 0.20)))
        probe_candidates = city_candidates[:probe_size]
        remaining_candidates = city_candidates[probe_size:]

        print(f"City {city}: Probing {len(probe_candidates)} tiles in Wave 1...")
        probed_results = {}
        with ThreadPoolExecutor(max_workers=num_workers) as ex:
            future_to_item = {
                ex.submit(download_file, item[2], raw_dir): item  # item[2] is agl_path
                for item in probe_candidates
            }
            for fut in as_completed(future_to_item):
                item = future_to_item[fut]
                agl_file = fut.result()
                tall_f, mean_h, p99_h = compute_tile_tall_fraction(agl_file)
                probed_results[item[0]] = {
                    "item": item,
                    "tall_frac": tall_f,
                    "mean_height": mean_h,
                    "p99_height": p99_h,
                }

        tall_fracs = [r["tall_frac"] for r in probed_results.values()]
        mean_tall = float(np.mean(tall_fracs))
        p75_tall = float(np.percentile(tall_fracs, 75))
        wave1_stats[city] = {
            "probed_count": len(probed_results),
            "mean_tall_pixel_frac": mean_tall,
            "median_tall_pixel_frac": float(np.median(tall_fracs)),
            "p75_tall_pixel_frac": p75_tall,
            "max_tall_pixel_frac": float(np.max(tall_fracs)),
            "tiles_with_tall_structures_ge_05": int(sum(1 for f in tall_fracs if f >= 0.05)),
        }
        print(f"  Wave 1 {city} stats: mean tall frac = {mean_tall:.4f}, p75 = {p75_tall:.4f}, "
              f"tiles >=0.05 tall = {wave1_stats[city]['tiles_with_tall_structures_ge_05']}/{len(tall_fracs)}")

        # Wave 2 Stratification:
        # Prioritize tiles with tall structures from probed results, then fill quota
        tall_probed = [r["item"] for b, r in probed_results.items() if r["tall_frac"] >= 0.05]
        low_probed = [r["item"] for b, r in probed_results.items() if r["tall_frac"] < 0.05]

        # Order probed tiles: all tall first (sorted descending by tall_frac), then low
        tall_probed.sort(key=lambda it: probed_results[it[0]]["tall_frac"], reverse=True)
        city_selected = list(tall_probed)

        # If more tiles needed, add remaining unprobed candidates and low probed candidates
        additional_needed = target_n - len(city_selected)
        pool_to_draw = remaining_candidates + low_probed
        RNG.shuffle(pool_to_draw)
        city_selected.extend(pool_to_draw[:additional_needed])

        city_selected = city_selected[:target_n]
        assert len(city_selected) == target_n, f"Could not satisfy quota for {city}: {len(city_selected)} vs {target_n}"
        selected_train_tiles.extend(city_selected)
        print(f"  City {city}: Selected {len(city_selected)} tiles (including {len(tall_probed)} tall-structure tiles).")

    return selected_train_tiles, wave1_stats


def extract_crops_from_tile(
    tile_name: str,
    split: str,
    city: str,
    rgb_path: Path,
    agl_path: Path,
    cls_path: Path,
    output_dir: Path,
    quarantine_dir: Path,
) -> Tuple[List[Dict], List[Dict]]:
    """Extract 4 crops (518x518) at offsets (0, 0), (0, 506), (506, 0), (506, 506).

    Applies QC checks and returns (passed_crop_rows, qc_drop_quarantine_rows).
    """
    with h5py.File(rgb_path, "r") as f_rgb:
        rgb = f_rgb["image"][()]
    with h5py.File(agl_path, "r") as f_agl:
        ndsm = f_agl["image"][()]
    with h5py.File(cls_path, "r") as f_cls:
        cls_arr = f_cls["image"][()].astype(np.uint8)

    crop_size = 518
    offsets = [(0, 0), (0, 506), (506, 0), (506, 506)]

    passed_rows = []
    qc_rows = []

    city_ceiling = CITY_CEILINGS.get(city, 500.0)

    for idx, (r, c) in enumerate(offsets):
        crop_id = f"{split}_{tile_name}_crop{idx}"
        crop_rgb = rgb[r : r + crop_size, c : c + crop_size]
        crop_ndsm = ndsm[r : r + crop_size, c : c + crop_size].astype(np.float32)
        crop_cls = cls_arr[r : r + crop_size, c : c + crop_size]

        # Valid mask: finite and non-negative
        valid_mask = np.isfinite(crop_ndsm) & (crop_ndsm >= 0.0)
        total_px = crop_size * crop_size
        valid_px = int(np.sum(valid_mask))
        nan_fraction = 1.0 - (valid_px / float(total_px))

        # QC Check 1: Drop if NaN / nodata fraction > 30%
        if nan_fraction > 0.30:
            qc_rows.append({
                "crop_id": crop_id,
                "city": city,
                "split": split,
                "tile_name": tile_name,
                "action": "drop",
                "reason": "nan_fraction_gt_30_percent",
                "nan_fraction": round(nan_fraction, 4),
            })
            continue

        # QC Check 2: Drop if any finite height < -1.0 m (physically implausible)
        finite_vals = crop_ndsm[np.isfinite(crop_ndsm)]
        if finite_vals.size > 0 and np.any(finite_vals < -1.0):
            qc_rows.append({
                "crop_id": crop_id,
                "city": city,
                "split": split,
                "tile_name": tile_name,
                "action": "drop",
                "reason": "height_lt_minus_1m",
                "min_height": float(np.min(finite_vals)),
            })
            continue

        # QC Check 3: Quarantine if p99.9 height exceeds per-city plausibility ceiling
        valid_vals = crop_ndsm[valid_mask]
        p99_9 = float(np.percentile(valid_vals, 99.9)) if valid_vals.size > 0 else 0.0
        if p99_9 > city_ceiling:
            # Quarantine crop
            q_file = quarantine_dir / f"{crop_id}.npz"
            np.savez_compressed(
                q_file,
                image=crop_rgb,
                depth=crop_ndsm,
                mask=valid_mask,
                cls=crop_cls,
            )
            qc_rows.append({
                "crop_id": crop_id,
                "city": city,
                "split": split,
                "tile_name": tile_name,
                "action": "quarantine",
                "reason": f"p99_9_gt_city_ceiling_{city_ceiling}m",
                "p99_9_height": round(p99_9, 2),
                "quarantined_path": str(q_file),
            })
            continue

        # QC Check 4: Drop if entirely class 0 / background
        valid_cls = crop_cls[valid_mask]
        if valid_cls.size > 0 and np.all(valid_cls == 0):
            qc_rows.append({
                "crop_id": crop_id,
                "city": city,
                "split": split,
                "tile_name": tile_name,
                "action": "drop",
                "reason": "entirely_class_0_background",
            })
            continue

        # Passed QC -> Save compressed crop .npz
        crop_file = output_dir / split / f"{crop_id}.npz"
        np.savez_compressed(
            crop_file,
            image=crop_rgb,
            depth=crop_ndsm,
            mask=valid_mask,
            cls=crop_cls,
        )

        # Compute crop band statistics
        h_min = float(np.min(valid_vals)) if valid_vals.size > 0 else 0.0
        h_max = float(np.max(valid_vals)) if valid_vals.size > 0 else 0.0
        h_mean = float(np.mean(valid_vals)) if valid_vals.size > 0 else 0.0
        h_median = float(np.median(valid_vals)) if valid_vals.size > 0 else 0.0
        h_p99 = float(np.percentile(valid_vals, 99)) if valid_vals.size > 0 else 0.0

        b_0_2 = float(np.mean((valid_vals >= 0.0) & (valid_vals < 2.0))) if valid_vals.size > 0 else 0.0
        b_2_5 = float(np.mean((valid_vals >= 2.0) & (valid_vals < 5.0))) if valid_vals.size > 0 else 0.0
        b_5_15 = float(np.mean((valid_vals >= 5.0) & (valid_vals < 15.0))) if valid_vals.size > 0 else 0.0
        b_15_30 = float(np.mean((valid_vals >= 15.0) & (valid_vals < 30.0))) if valid_vals.size > 0 else 0.0
        b_30_inf = float(np.mean(valid_vals >= 30.0)) if valid_vals.size > 0 else 0.0

        # Class counts
        cls_counts = {k: 0 for k in range(7)}
        if valid_cls.size > 0:
            c_ids, c_cnts = np.unique(valid_cls, return_counts=True)
            for cid, ccnt in zip(c_ids, c_cnts):
                if 0 <= cid <= 6:
                    cls_counts[int(cid)] = int(ccnt)

        row = {
            "crop_id": crop_id,
            "city": city,
            "source_tile": tile_name,
            "split": split,
            "crop_offsets": f"{r}_{c}",
            "file_path": str(crop_file.relative_to(output_dir.parent.parent)).replace("\\", "/"),
            "valid_pixels": valid_px,
            "nan_fraction": round(nan_fraction, 4),
            "height_min": round(h_min, 3),
            "height_max": round(h_max, 3),
            "height_mean": round(h_mean, 3),
            "height_median": round(h_median, 3),
            "height_p99": round(h_p99, 3),
            "band_0_2": round(b_0_2, 4),
            "band_2_5": round(b_2_5, 4),
            "band_5_15": round(b_5_15, 4),
            "band_15_30": round(b_15_30, 4),
            "band_30_inf": round(b_30_inf, 4),
            "count_cls0": cls_counts[0],
            "count_cls1": cls_counts[1],
            "count_cls2": cls_counts[2],
            "count_cls3": cls_counts[3],
            "count_cls4": cls_counts[4],
            "count_cls5": cls_counts[5],
            "count_cls6": cls_counts[6],
        }
        passed_rows.append(row)

    return passed_rows, qc_rows


def run_pipeline():
    t_start_total = time.time()
    repo_root = Path(__file__).resolve().parent.parent
    raw_dir = repo_root / "data" / "gamus_raw"
    output_dir = repo_root / "data" / "gamus"
    quarantine_dir = output_dir / "quarantine"
    artifacts_dir = repo_root / "artifacts" / "v1.1.0"

    raw_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    for sp in ["train", "val", "test"]:
        (output_dir / sp).mkdir(parents=True, exist_ok=True)

    print("Loading candidate triplets from artifacts/v1.1.0/hf_file_list.txt...")
    triplets = load_hf_triplets(artifacts_dir / "hf_file_list.txt")

    # Step 1: Select Val & Test deterministically (unstratified, representative)
    print("\n--- Selecting Held-out Validation & Test Sets (Unstratified) ---")
    val_selected = []
    for city in ["DC", "PHL"]:  # NYC has 0 in official val
        pool = list(triplets["val"][city])
        RNG.shuffle(pool)
        val_selected.extend(pool[: TARGET_QUOTAS["val"][city]])
    print(f"Val tiles selected: {len(val_selected)} (DC: {TARGET_QUOTAS['val']['DC']}, PHL: {TARGET_QUOTAS['val']['PHL']})")

    test_selected = []
    for city in ["DC", "NYC", "PHL"]:
        pool = list(triplets["test"][city])
        RNG.shuffle(pool)
        test_selected.extend(pool[: TARGET_QUOTAS["test"][city]])
    print(f"Test tiles selected: {len(test_selected)} (DC: 100, NYC: 100, PHL: 100)")

    # Step 2: Select Train with Wave 1 & Wave 2 stratification
    train_selected, wave1_stats = wave1_and_wave2_train_selection(
        triplets["train"], TARGET_QUOTAS["train"], raw_dir, num_workers=16
    )

    # Assert split disjointness programmatically
    set_train = set(it[0] for it in train_selected)
    set_val = set(it[0] for it in val_selected)
    set_test = set(it[0] for it in test_selected)
    inter_train_val = set_train & set_val
    inter_train_test = set_train & set_test
    inter_val_test = set_val & set_test

    print("\n--- Split Intersection Assertions ---")
    print(f"Train / Val intersection count: {len(inter_train_val)}")
    print(f"Train / Test intersection count: {len(inter_train_test)}")
    print(f"Val / Test intersection count: {len(inter_val_test)}")
    assert len(inter_train_val) == 0, f"Train and Val share {len(inter_train_val)} tiles!"
    assert len(inter_train_test) == 0, f"Train and Test share {len(inter_train_test)} tiles!"
    assert len(inter_val_test) == 0, f"Val and Test share {len(inter_val_test)} tiles!"
    print("ALL SPLITS ARE STRICTLY DISJOINT.")

    # Step 3: Build complete download task list
    # Item structure: (split, city, base_clean, img_rel_path, agl_rel_path, cls_rel_path)
    all_tile_tasks = []
    for base, img_p, agl_p, cls_p in train_selected:
        all_tile_tasks.append(("train", base.split("_")[0], base, img_p, agl_p, cls_p))
    for base, img_p, agl_p, cls_p in val_selected:
        all_tile_tasks.append(("val", base.split("_")[0], base, img_p, agl_p, cls_p))
    for base, img_p, agl_p, cls_p in test_selected:
        all_tile_tasks.append(("test", base.split("_")[0], base, img_p, agl_p, cls_p))

    print(f"\nTotal tiles to process: {len(all_tile_tasks)} (Train: {len(train_selected)}, Val: {len(val_selected)}, Test: {len(test_selected)})")

    # Download in parallel batches and process crops
    all_manifest_rows = []
    all_qc_rows = []

    print("\nDownloading triplets and extracting 518x518 crops with QC filtering...")
    # Pre-download missing files in parallel
    files_to_download = []
    for split, city, base, img_p, agl_p, cls_p in all_tile_tasks:
        files_to_download.append(img_p)
        files_to_download.append(agl_p)
        files_to_download.append(cls_p)

    print(f"Total HDF5 files to verify/download: {len(files_to_download)}")
    completed_dl = 0
    t0_dl = time.time()
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(download_file, f, raw_dir): f for f in files_to_download}
        for fut in as_completed(futures):
            fut.result()
            completed_dl += 1
            if completed_dl % 500 == 0 or completed_dl == len(files_to_download):
                elapsed = time.time() - t0_dl
                print(f"  Verified/downloaded {completed_dl}/{len(files_to_download)} files in {elapsed:.1f}s ({completed_dl/elapsed:.1f} files/s)")

    print("\nAll raw files ready. Extracting crops...")
    t0_crop = time.time()
    for idx, (split, city, base, img_p, agl_p, cls_p) in enumerate(all_tile_tasks):
        rgb_p = raw_dir / img_p
        agl_p = raw_dir / agl_p
        cls_p = raw_dir / cls_p

        passed, qc = extract_crops_from_tile(
            tile_name=base,
            split=split,
            city=city,
            rgb_path=rgb_p,
            agl_path=agl_p,
            cls_path=cls_p,
            output_dir=output_dir,
            quarantine_dir=quarantine_dir,
        )
        all_manifest_rows.extend(passed)
        all_qc_rows.extend(qc)

        if (idx + 1) % 250 == 0 or (idx + 1) == len(all_tile_tasks):
            print(f"  Processed {idx + 1}/{len(all_tile_tasks)} tiles -> {len(all_manifest_rows)} crops passed, {len(all_qc_rows)} QC events")


    # Step 4: Write Manifest CSV
    manifest_csv = output_dir / "manifest.csv"
    fieldnames = [
        "crop_id", "city", "source_tile", "split", "crop_offsets", "file_path",
        "valid_pixels", "nan_fraction", "height_min", "height_max", "height_mean",
        "height_median", "height_p99", "band_0_2", "band_2_5", "band_5_15",
        "band_15_30", "band_30_inf", "count_cls0", "count_cls1", "count_cls2",
        "count_cls3", "count_cls4", "count_cls5", "count_cls6",
    ]
    with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_manifest_rows)
    print(f"\nWrote manifest with {len(all_manifest_rows)} crops to {manifest_csv}")

    # Step 5: Write QC Report JSON
    qc_report = {
        "total_qc_events": len(all_qc_rows),
        "by_action": defaultdict(int),
        "by_reason": defaultdict(int),
        "by_city": defaultdict(int),
        "by_split": defaultdict(int),
        "events": all_qc_rows,
    }
    for r in all_qc_rows:
        qc_report["by_action"][r["action"]] += 1
        qc_report["by_reason"][r["reason"]] += 1
        qc_report["by_city"][r["city"]] += 1
        qc_report["by_split"][r["split"]] += 1

    qc_report["by_action"] = dict(qc_report["by_action"])
    qc_report["by_reason"] = dict(qc_report["by_reason"])
    qc_report["by_city"] = dict(qc_report["by_city"])
    qc_report["by_split"] = dict(qc_report["by_split"])

    qc_json = artifacts_dir / "data_qc_report.json"
    qc_json.write_text(json.dumps(qc_report, indent=2))
    print(f"Wrote data QC report to {qc_json}")
    print("QC Summary:")
    print(f"  Actions: {qc_report['by_action']}")
    print(f"  Reasons: {qc_report['by_reason']}")

    # Step 6: Verify crop counts against acceptance criteria
    split_counts = defaultdict(int)
    city_counts = defaultdict(lambda: defaultdict(int))
    for r in all_manifest_rows:
        split_counts[r["split"]] += 1
        city_counts[r["split"]][r["city"]] += 1

    print("\n--- Realised Crop Counts ---")
    for sp in ["train", "val", "test"]:
        print(f"Split {sp}: {split_counts[sp]} crops (by city: {dict(city_counts[sp])})")

    assert split_counts["train"] >= 3000, f"Train crop count {split_counts['train']} < 3000 requirement!"
    assert split_counts["val"] >= 400, f"Val crop count {split_counts['val']} < 400 requirement!"
    assert split_counts["test"] >= 900, f"Test crop count {split_counts['test']} < 900 requirement!"
    print("ALL MINIMUM CROP THRESHOLDS SATISFIED.")

    # Step 7: Compute Corpus Statistics & Height Distribution Figure
    print("\n--- Computing Corpus Statistics & Generating Height Distribution Plot ---")
    # Sample height pixels across all splits for histogram and stats
    city_height_samples = defaultdict(list)
    city_tall_pixels = defaultdict(int)
    city_total_pixels = defaultdict(int)

    for sp in ["train", "val", "test"]:
        sp_dir = output_dir / sp
        for crop_p in sp_dir.glob("*.npz"):
            with np.load(crop_p) as d:
                depth = d["depth"]
                mask = d["mask"]
                city = crop_p.stem.split("_")[1]
                v_depth = depth[mask]
                if v_depth.size > 0:
                    city_total_pixels[city] += int(v_depth.size)
                    city_tall_pixels[city] += int(np.sum(v_depth >= 15.0))
                    # Subsample for plotting
                    if len(city_height_samples[city]) < 100000:
                        sub = v_depth[np.random.choice(v_depth.size, min(v_depth.size, 500), replace=False)]
                        city_height_samples[city].extend(sub.tolist())

    dataset_stats = {
        "realised_crops": dict(split_counts),
        "crops_by_city": {k: dict(v) for k, v in city_counts.items()},
        "total_crops": len(all_manifest_rows),
        "city_tall_pixel_fractions": {
            city: round(city_tall_pixels[city] / max(1, city_total_pixels[city]), 5)
            for city in ["DC", "NYC", "PHL"]
        },
        "city_pixel_totals": {
            city: {
                "total_valid_pixels": city_total_pixels[city],
                "tall_pixels_ge_15m": city_tall_pixels[city],
                "tall_fraction_pct": round((city_tall_pixels[city] / max(1, city_total_pixels[city])) * 100, 3)
            }
            for city in ["DC", "NYC", "PHL"]
        },
        "wave1_probe_stats": wave1_stats,
    }

    stats_json = artifacts_dir / "dataset_stats_v1.1.0.json"
    stats_json.write_text(json.dumps(dataset_stats, indent=2))
    print(f"Saved dataset statistics to {stats_json}")

    print("\nMeasured Tall-Pixel (>=15 m) Fraction Per City:")
    for city in ["DC", "NYC", "PHL"]:
        pct = dataset_stats["city_pixel_totals"][city]["tall_fraction_pct"]
        print(f"  {city}: {pct:.3f}% ({city_tall_pixels[city]:,} / {city_total_pixels[city]:,} valid pixels)")

    # Plot Height Distribution
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # All cities combined
    all_samples = []
    for c in ["DC", "NYC", "PHL"]:
        all_samples.extend(city_height_samples[c])

    ax_all = axes[0, 0]
    ax_all.hist(all_samples, bins=60, range=(0, 60), color="#1f77b4", edgecolor="black", alpha=0.75, density=True)
    med_all = float(np.median(all_samples))
    p99_all = float(np.percentile(all_samples, 99))
    ax_all.axvline(med_all, color="orange", linestyle="--", linewidth=2, label=f"Median: {med_all:.2f} m")
    ax_all.axvline(p99_all, color="red", linestyle=":", linewidth=2, label=f"p99: {p99_all:.2f} m")
    ax_all.set_title("Overall GAMUS v1.1.0 Height Distribution (0 - 60 m)")
    ax_all.set_xlabel("nDSM Height (m)")
    ax_all.set_ylabel("Density")
    ax_all.legend()
    ax_all.grid(True, linestyle="--", alpha=0.5)

    # Per-city plots
    city_names = {"DC": "Washington DC", "NYC": "New York City", "PHL": "Philadelphia"}
    city_colors = {"DC": "#2ca02c", "NYC": "#d62728", "PHL": "#9467bd"}
    for idx, (city, ax) in enumerate(zip(["DC", "NYC", "PHL"], [axes[0, 1], axes[1, 0], axes[1, 1]])):
        c_samples = city_height_samples[city]
        ax.hist(c_samples, bins=60, range=(0, 60), color=city_colors[city], edgecolor="black", alpha=0.75, density=True)
        c_med = float(np.median(c_samples))
        c_p99 = float(np.percentile(c_samples, 99))
        c_tall_pct = dataset_stats["city_pixel_totals"][city]["tall_fraction_pct"]
        ax.axvline(c_med, color="orange", linestyle="--", linewidth=2, label=f"Median: {c_med:.2f} m")
        ax.axvline(c_p99, color="red", linestyle=":", linewidth=2, label=f"p99: {c_p99:.2f} m")
        ax.set_title(f"{city_names[city]} (Tall >=15m: {c_tall_pct:.2f}%)")
        ax.set_xlabel("nDSM Height (m)")
        ax.set_ylabel("Density")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)

    plt.suptitle("GAMUS v1.1.0 Long-Tailed Height Distribution Analysis\n(Reproducing Xiong et al. 2023 Sec 3.2)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plot_path = artifacts_dir / "height_distribution.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Saved height distribution figure to {plot_path}")

    elapsed_total = time.time() - t_start_total
    print(f"\n=== Phase 3 Complete in {elapsed_total/60:.2f} minutes ===")


if __name__ == "__main__":
    run_pipeline()
