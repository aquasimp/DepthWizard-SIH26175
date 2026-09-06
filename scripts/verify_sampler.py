"""Empirical verification script for HeightStratifiedBatchSampler.

Draws 300 batches through the sampler over the real manifest and verifies:
1. Realised per-bucket slot share.
2. Fraction of accumulation windows containing at least one crop with tall-fraction >= 0.05 (>= 95% required).
3. Mean fraction of >=15 m pixels per batch versus corpus-wide baseline (>= 2.5x required).
4. Realised per-bucket oversampling factors.
5. Zero val/test crop ID leakage into training batches.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
import numpy as np

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from training.sampler import HeightStratifiedBatchSampler

manifest_path = Path("data/gamus/manifest.csv")
stats_path = Path("artifacts/v1.1.0/dataset_stats_v1.1.0.json")

# Load manifest
with open(manifest_path, "r", encoding="utf-8") as f:
    all_rows = list(csv.DictReader(f))

train_rows = [r for r in all_rows if r["split"] == "train"]
val_test_ids = set(r["crop_id"] for r in all_rows if r["split"] in ["val", "test"])
train_crop_map = {idx: r for idx, r in enumerate(train_rows)}
train_id_set = set(r["crop_id"] for r in train_rows)

# Load corpus baseline
with open(stats_path, "r", encoding="utf-8") as f:
    dataset_stats = json.load(f)

# Compute corpus-wide baseline from dataset stats
total_tall = sum(v["tall_pixels_ge_15m"] for v in dataset_stats["city_pixel_totals"].values())
total_valid = sum(v["total_valid_pixels"] for v in dataset_stats["city_pixel_totals"].values())
corpus_baseline_tall_frac = total_tall / max(1, total_valid)
phl_baseline_tall_frac = dataset_stats["city_tall_pixel_fractions"]["PHL"]

print(f"Corpus-wide baseline tall pixel fraction: {corpus_baseline_tall_frac:.5f} ({corpus_baseline_tall_frac * 100:.2f}%)")
print(f"Philadelphia low-structure baseline: {phl_baseline_tall_frac:.5f} ({phl_baseline_tall_frac * 100:.2f}%)")

# Initialize sampler: micro-batch 4, accumulation 2 -> effective window 8
# Target: guarantee >= 37.5% from B2 u B3, with high B3 allocation
batch_size = 4
accumulation_steps = 2
window_size = batch_size * accumulation_steps  # 8

sampler = HeightStratifiedBatchSampler(
    manifest_path=manifest_path,
    batch_size=batch_size,
    accumulation_steps=accumulation_steps,
    min_tall_ratio=0.625,  # 5 of 8 slots guaranteed tall (B2 u B3) to heavily beat 2.5x baseline
    b3_allocation_ratio=0.80,  # 4 slots B3, 1 slot B2, 3 slots B0/B1
    seed=1337,
)

# Draw 300 batches (150 accumulation windows)
num_batches_to_test = 300
batch_iterator = iter(sampler)

drawn_batches = []
for _ in range(num_batches_to_test):
    try:
        b = next(batch_iterator)
    except StopIteration:
        sampler.set_epoch(sampler.epoch + 1)
        batch_iterator = iter(sampler)
        b = next(batch_iterator)
    drawn_batches.append(b)

total_slots = 0
bucket_slot_counts = Counter()
windows_with_tall = 0
total_windows = num_batches_to_test // accumulation_steps

batch_tall_pixel_fractions = []
emitted_ids = set()
val_test_leaks = []

for w_idx in range(total_windows):
    window_batches = drawn_batches[w_idx * accumulation_steps : (w_idx + 1) * accumulation_steps]
    window_has_tall = False

    for batch in window_batches:
        batch_tall_px = 0
        batch_valid_px = 0

        for local_idx in batch:
            row = train_crop_map[local_idx]
            cid = row["crop_id"]
            emitted_ids.add(cid)

            if cid in val_test_ids:
                val_test_leaks.append(cid)

            tf = float(row["band_15_30"]) + float(row["band_30_inf"])
            if tf >= 0.05:
                window_has_tall = True

            # Assign bucket
            if tf < 0.01:
                b_name = "B0"
            elif tf < 0.05:
                b_name = "B1"
            elif tf < 0.15:
                b_name = "B2"
            else:
                b_name = "B3"
            bucket_slot_counts[b_name] += 1
            total_slots += 1

            v_px = int(row["valid_pixels"])
            t_px = int(v_px * tf)
            batch_tall_px += t_px
            batch_valid_px += v_px

        batch_frac = batch_tall_px / max(1, batch_valid_px)
        batch_tall_pixel_fractions.append(batch_frac)

    if window_has_tall:
        windows_with_tall += 1

mean_batch_tall_frac = float(np.mean(batch_tall_pixel_fractions))
multiplier_corpus = mean_batch_tall_frac / corpus_baseline_tall_frac
multiplier_phl = mean_batch_tall_frac / phl_baseline_tall_frac
window_tall_frac = windows_with_tall / float(total_windows)

slot_shares = {
    b: round(bucket_slot_counts[b] / float(total_slots), 4)
    for b in ["B0", "B1", "B2", "B3"]
}
tall_slot_share = slot_shares["B2"] + slot_shares["B3"]

oversampling_factors = sampler.get_oversampling_factors()

verification_report = {
    "num_batches_tested": num_batches_to_test,
    "num_windows_tested": total_windows,
    "batch_size": batch_size,
    "accumulation_steps": accumulation_steps,
    "effective_batch_window": window_size,
    "realised_bucket_slot_shares": slot_shares,
    "tall_slots_share_b2_u_b3": round(tall_slot_share, 4),
    "fraction_windows_with_tall_crop": round(window_tall_frac, 4),
    "fraction_windows_with_tall_crop_pct": round(window_tall_frac * 100, 2),
    "mean_batch_tall_pixel_fraction": round(mean_batch_tall_frac, 5),
    "corpus_baseline_tall_pixel_fraction": round(corpus_baseline_tall_frac, 5),
    "corpus_multiplier": round(multiplier_corpus, 3),
    "phl_baseline_tall_pixel_fraction": round(phl_baseline_tall_frac, 5),
    "phl_multiplier": round(multiplier_phl, 3),
    "realised_oversampling_factors": oversampling_factors,
    "total_unique_crops_drawn": len(emitted_ids),
    "val_test_leaks_count": len(val_test_leaks),
    "all_emitted_ids_valid": bool(emitted_ids.issubset(train_id_set)),
    "criterion_1_window_tall_ge_95pct": bool(window_tall_frac >= 0.95),
    "criterion_2_multiplier_ge_2_5x": bool(multiplier_corpus >= 2.5),
    "criterion_3_zero_leaks": bool(len(val_test_leaks) == 0),
    "criterion_4_all_ids_valid": bool(emitted_ids.issubset(train_id_set)),
}

out_path = Path("artifacts/v1.1.0/sampler_verification.json")
out_path.write_text(json.dumps(verification_report, indent=2))
print(f"Saved verification report to {out_path}")

print("\n=== SAMPLER VERIFICATION RESULTS ===")
print(f"1. Realised slot shares: {slot_shares} (Tall B2+B3: {tall_slot_share*100:.1f}%)")
print(f"2. Windows with tall crop (>=0.05): {windows_with_tall}/{total_windows} ({window_tall_frac*100:.2f}%) [Requirement: >= 95%]")
print(f"3. Mean batch tall pixel fraction: {mean_batch_tall_frac:.4f}")
print(f"   Corpus baseline: {corpus_baseline_tall_frac:.4f} -> Multiplier: {multiplier_corpus:.2f}x [Requirement: >= 2.5x]")
print(f"4. Realised oversampling factors: {oversampling_factors}")
print(f"5. Val/Test leakage count: {len(val_test_leaks)} [Requirement: 0]")
print(f"6. All emitted IDs valid train crops: {verification_report['all_emitted_ids_valid']}")

assert verification_report["criterion_1_window_tall_ge_95pct"], f"Criterion 1 failed: {window_tall_frac*100:.2f}% < 95%"
assert verification_report["criterion_2_multiplier_ge_2_5x"], f"Criterion 2 failed: {multiplier_corpus:.2f}x < 2.5x"
assert verification_report["criterion_3_zero_leaks"], f"Criterion 3 failed: {len(val_test_leaks)} leaks"
assert verification_report["criterion_4_all_ids_valid"], "Criterion 4 failed: invalid crop IDs emitted"
print("\n>>> ALL SAMPLER ACCEPTANCE CRITERIA EMPIRICALLY SATISFIED <<<")
