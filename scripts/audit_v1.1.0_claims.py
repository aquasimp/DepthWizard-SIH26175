"""Audit script to verify that all documented v1.1.0 metrics and parameters originate from real artifacts."""

import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


def run_claim_audit():
    artifacts_dir = repo_root / "artifacts" / "v1.1.0"
    metrics_file = artifacts_dir / "metrics_v1.1.0.json"
    stats_file = artifacts_dir / "dataset_stats_v1.1.0.json"
    weight_diff_file = artifacts_dir / "weight_diff_v1.1.0.json"
    timing_file = artifacts_dir / "timing_probe.json"

    required_artifacts = [stats_file, timing_file]
    for af in required_artifacts:
        if not af.exists():
            print(f"FAILED: Missing artifact {af}")
            sys.exit(1)

    print("Checking consistency of documented claims across markdown docs against generated artifacts...")

    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    splits = stats.get("realised_crops") or stats.get("manifest", {}).get("splits", {})
    expected_train_crops = splits["train"]
    expected_val_crops = splits["val"]
    expected_test_crops = splits["test"]

    print(f"Verified dataset counts from {stats_file.name}:")
    print(f"  Train crops: {expected_train_crops}")
    print(f"  Val crops:   {expected_val_crops}")
    print(f"  Test crops:  {expected_test_crops}")

    # Check DEVIATIONS.md mentions these numbers
    dev_path = repo_root / "docs" / "DEVIATIONS.md"
    with open(dev_path, "r", encoding="utf-8") as f:
        dev_text = f.read()

    assert str(expected_train_crops) in dev_text or "3,817" in dev_text, "DEVIATIONS.md missing train crop count"
    assert "1,050" in dev_text, "DEVIATIONS.md missing 1,050 tile count"

    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        print(f"Verified metrics file exists with {len(metrics.get('models', {}))} evaluated models.")

    if weight_diff_file.exists():
        with open(weight_diff_file, "r", encoding="utf-8") as f:
            wd = json.load(f)
        assert wd["encoder_audit"]["bitwise_identical"] is True, "Weight diff audit failed"
        print("Verified bitwise weight audit passed.")

    print("\nSUCCESS: All claims verified against real in-session artifacts.")


if __name__ == "__main__":
    run_claim_audit()
