"""Download and prepare a stratified subset of the GAMUS dataset.

Downloads paired RGB and metric nDSM (AGL) tiles from Hugging Face (earthflow/GAMUS),
crops 1024x1024 tiles to canonical 518x518 patches, filters crops with >40% nodata,
and produces a manifest CSV and height distribution histogram.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import h5py
import matplotlib.pyplot as plt
import numpy as np
from huggingface_hub import HfApi, hf_hub_download


def extract_crops(
    rgb: np.ndarray,
    ndsm: np.ndarray,
    crop_size: int = 518,
) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray, int]]:
    """Extract 4 overlapping crops of size (crop_size, crop_size) from 1024x1024."""
    H, W = ndsm.shape
    crops = []
    offsets = [
        (0, 0),
        (0, W - crop_size),
        (H - crop_size, 0),
        (H - crop_size, W - crop_size),
    ]

    for idx, (r, c) in enumerate(offsets):
        crop_rgb = rgb[r : r + crop_size, c : c + crop_size]
        crop_ndsm = ndsm[r : r + crop_size, c : c + crop_size]

        # Valid mask: finite and non-negative (GAMUS nDSM is height above ground in metres)
        mask = np.isfinite(crop_ndsm) & (crop_ndsm >= 0.0) & (crop_ndsm < 500.0)
        nodata_fraction = 1.0 - (np.sum(mask) / float(crop_size * crop_size))

        if nodata_fraction <= 0.40:
            clean_ndsm = np.where(mask, crop_ndsm, 0.0).astype(np.float32)
            crops.append((crop_rgb, clean_ndsm, mask, idx))

    return crops


def prepare_gamus(
    output_dir: str = "data/gamus",
    max_train_tiles: int = 150,
    max_val_tiles: int = 30,
) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "train").mkdir(parents=True, exist_ok=True)
    (out_path / "val").mkdir(parents=True, exist_ok=True)

    print("Querying earthflow/GAMUS repository on Hugging Face...")
    api = HfApi()
    all_files = api.list_repo_files(repo_id="earthflow/GAMUS", repo_type="dataset")

    manifest_rows = []
    all_p99_heights = []
    sampled_height_vals: List[float] = []

    for split, max_tiles in [("train", max_train_tiles), ("val", max_val_tiles)]:
        split_prefix = f"images/{split}/"
        candidate_rgb_files = [f for f in all_files if f.startswith(split_prefix) and f.endswith("_RGB.h5")]

        # Group by city for stratification
        cities: Dict[str, List[str]] = {}
        for f in candidate_rgb_files:
            city = f.split("/")[-1].split("_")[0]
            cities.setdefault(city, []).append(f)

        # Stratified sampling
        selected_files: List[str] = []
        city_names = sorted(cities.keys())
        per_city = max(1, max_tiles // len(city_names))
        for city in city_names:
            selected_files.extend(cities[city][:per_city])
        selected_files = selected_files[:max_tiles]

        print(f"Split {split}: Processing {len(selected_files)} tiles across {city_names}...")

        for _file_idx, rgb_rel_path in enumerate(selected_files):
            tile_name = Path(rgb_rel_path).stem.replace("_RGB", "")
            hgt_rel_path = f"heights/{split}/{tile_name}_AGL.h5"
            city = tile_name.split("_")[0]

            try:
                rgb_path = hf_hub_download(repo_id="earthflow/GAMUS", repo_type="dataset", filename=rgb_rel_path)
                hgt_path = hf_hub_download(repo_id="earthflow/GAMUS", repo_type="dataset", filename=hgt_rel_path)

                with h5py.File(rgb_path, "r") as f_rgb:
                    rgb = f_rgb["image"][:]
                with h5py.File(hgt_path, "r") as f_hgt:
                    ndsm = f_hgt["image"][:]

                crops = extract_crops(rgb, ndsm, crop_size=518)
                for crop_rgb, crop_ndsm, mask, crop_idx in crops:
                    crop_id = f"{split}_{tile_name}_crop{crop_idx}"
                    crop_file = out_path / split / f"{crop_id}.npz"

                    np.savez_compressed(
                        crop_file,
                        image=crop_rgb,
                        depth=crop_ndsm,
                        mask=mask,
                    )

                    valid_h = crop_ndsm[mask]
                    if len(valid_h) > 0:
                        h_mean = float(np.mean(valid_h))
                        h_max = float(np.max(valid_h))
                        h_p99 = float(np.percentile(valid_h, 99))
                        all_p99_heights.append(h_p99)
                        if len(sampled_height_vals) < 50000:
                            sampled_height_vals.extend(valid_h[valid_h > 0.5][:200].tolist())
                    else:
                        h_mean, h_max, h_p99 = 0.0, 0.0, 0.0

                    manifest_rows.append({
                        "id": crop_id,
                        "split": split,
                        "city": city,
                        "tile_name": tile_name,
                        "crop_idx": crop_idx,
                        "file_path": str(crop_file.relative_to(out_path.parent.parent)),
                        "valid_ratio": float(np.mean(mask)),
                        "height_mean": round(h_mean, 3),
                        "height_max": round(h_max, 3),
                        "height_p99": round(h_p99, 3),
                    })

            except Exception as e:
                print(f"Error processing {tile_name}: {e}")

    # Write Manifest CSV
    manifest_path = out_path / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "split", "city", "tile_name", "crop_idx",
            "file_path", "valid_ratio", "height_mean", "height_max", "height_p99",
        ])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote manifest with {len(manifest_rows)} crops to {manifest_path}")

    # Generate Height Histogram PNG
    if sampled_height_vals:
        hist_path = out_path / "height_histogram.png"
        plt.figure(figsize=(8, 5))
        plt.hist(sampled_height_vals, bins=60, range=(0, 60), color="#0055a5", edgecolor="black", alpha=0.8)
        plt.title("GAMUS nDSM Height Distribution (Metres Above Ground)")
        plt.xlabel("Height (m)")
        plt.ylabel("Pixel Count")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.axvline(float(np.median(sampled_height_vals)), color="orange", linestyle="--", label=f"Median: {np.median(sampled_height_vals):.1f}m")
        plt.axvline(float(np.percentile(sampled_height_vals, 99)), color="red", linestyle=":", label=f"99th Percentile: {np.percentile(sampled_height_vals, 99):.1f}m")
        plt.legend()
        plt.tight_layout()
        plt.savefig(hist_path, dpi=150)
        plt.close()
        print(f"Saved height histogram to {hist_path}")

    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GAMUS dataset subset")
    parser.add_argument("--output-dir", default="data/gamus")
    parser.add_argument("--max-train-tiles", type=int, default=150)
    parser.add_argument("--max-val-tiles", type=int, default=30)
    args = parser.parse_args()

    prepare_gamus(
        output_dir=args.output_dir,
        max_train_tiles=args.max_train_tiles,
        max_val_tiles=args.max_val_tiles,
    )


if __name__ == "__main__":
    main()
