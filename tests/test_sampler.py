"""Unit tests for HeightStratifiedBatchSampler.

Tests:
1. Empty / pathologically small tall bucket raises ValueError.
2. Determinism under fixed seed (identical batch sequence).
3. Per-window guarantee (minimum tall slots in every window).
4. Zero leakage: val/test crops never emitted.
"""

import csv
from pathlib import Path

import pytest

from training.sampler import HeightStratifiedBatchSampler

MANIFEST_PATH = Path("data/gamus/manifest.csv")


def test_sampler_empty_tall_bucket_raises(tmp_path: Path) -> None:
    """Verify that an empty or pathologically small (<2%) tall bucket raises ValueError."""
    dummy_manifest = tmp_path / "dummy_manifest.csv"
    with open(dummy_manifest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["crop_id", "split", "band_15_30", "band_30_inf"])
        writer.writeheader()
        # 100 crops, all in B0 (0.0 tall fraction)
        for i in range(100):
            writer.writerow({
                "crop_id": f"train_crop_{i}",
                "split": "train",
                "band_15_30": "0.0",
                "band_30_inf": "0.0",
            })

    with pytest.raises(ValueError, match="below the mandatory 2.0% threshold"):
        HeightStratifiedBatchSampler(manifest_path=dummy_manifest, batch_size=4)


def test_sampler_determinism_under_fixed_seed() -> None:
    """Verify that identical seeds produce bitwise-identical batch sequences."""
    sampler1 = HeightStratifiedBatchSampler(
        manifest_path=MANIFEST_PATH, batch_size=4, accumulation_steps=2, seed=1337
    )
    sampler2 = HeightStratifiedBatchSampler(
        manifest_path=MANIFEST_PATH, batch_size=4, accumulation_steps=2, seed=1337
    )

    batches1 = [b for idx, b in enumerate(sampler1) if idx < 50]
    batches2 = [b for idx, b in enumerate(sampler2) if idx < 50]

    assert len(batches1) == len(batches2) == 50
    assert batches1 == batches2, "Batches differed under identical seed=1337!"


def test_sampler_per_window_guarantee() -> None:
    """Verify that every accumulation window satisfies the minimum tall structure guarantee."""
    batch_size = 4
    accumulation_steps = 2
    sampler = HeightStratifiedBatchSampler(
        manifest_path=MANIFEST_PATH,
        batch_size=batch_size,
        accumulation_steps=accumulation_steps,
        min_tall_ratio=0.375,
        seed=1337,
    )

    batches = [b for idx, b in enumerate(sampler) if idx < 40]
    # Check 20 windows (2 batches per window)
    for w in range(20):
        window = batches[w * 2] + batches[w * 2 + 1]
        assert len(window) == 8
        # Check tall fraction of each sample in window
        tall_slots = 0
        for local_idx in window:
            tf = sampler.tall_fractions[local_idx]
            if tf >= 0.05:  # B2 u B3
                tall_slots += 1

        assert tall_slots >= 3, f"Window {w} had only {tall_slots} tall slots (< 3 required for 37.5%)"


def test_sampler_zero_leakage_and_valid_ids() -> None:
    """Verify that no val or test crops are ever emitted and all emitted indices are train."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    val_test_crop_ids = set(r["crop_id"] for r in rows if r["split"] != "train")
    train_crop_ids = set(r["crop_id"] for r in rows if r["split"] == "train")

    sampler = HeightStratifiedBatchSampler(
        manifest_path=MANIFEST_PATH, batch_size=4, accumulation_steps=2, seed=1337
    )

    emitted_ids = set()
    for idx, batch in enumerate(sampler):
        if idx >= 50:
            break
        for local_idx in batch:
            cid = sampler.crop_ids[local_idx]
            emitted_ids.add(cid)

    # Assertions
    assert len(emitted_ids & val_test_crop_ids) == 0, "Val or test crop IDs leaked into sampler!"
    assert emitted_ids.issubset(train_crop_ids), "Non-train crop IDs found in sampler output!"
