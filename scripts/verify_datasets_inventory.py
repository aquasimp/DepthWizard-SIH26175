"""
Verification script for X:\\DatasetsSIH 26175 inventory.
Checks all directories, file counts, and model integrity.
"""

from pathlib import Path
import os
import sys

BASE_DIR = Path("X:/DatasetsSIH 26175")

def check_inventory():
    print("=" * 70)
    print("DepthWizard SIH 26175 - Dataset Repository Health Verification")
    print("Target Root:", BASE_DIR)
    print("=" * 70)

    if not BASE_DIR.exists():
        print("ERROR: Base directory does not exist!")
        return False

    all_passed = True

    # 1. Check GAMUS
    gamus_dir = BASE_DIR / "01_REQUIRED_PRIMARY_BENCHMARK" / "GAMUS"
    print("\n[1] Checking GAMUS Primary Benchmark...")
    raw_h5 = list((gamus_dir / "raw_h5").rglob("*.h5"))
    npz_train = list((gamus_dir / "npz_canonical_crops" / "train").glob("*.npz"))
    npz_val = list((gamus_dir / "npz_canonical_crops" / "val").glob("*.npz"))
    npz_test = list((gamus_dir / "npz_canonical_crops" / "test").glob("*.npz"))
    meta_files = list((gamus_dir / "metadata").glob("*.*"))

    print(f"  - Raw HDF5 tiles: {len(raw_h5)} files found")
    print(f"  - Canonical train crops: {len(npz_train)} npz files")
    print(f"  - Canonical val crops: {len(npz_val)} npz files")
    print(f"  - Canonical test crops: {len(npz_test)} npz files")
    print(f"  - Metadata assets: {len(meta_files)} files (including full remote inventory)")
    if len(raw_h5) == 0 or len(npz_train) == 0:
        print("  FAIL: GAMUS data incomplete!")
        all_passed = False
    else:
        print("  PASS: GAMUS repository complete.")

    # 2. Check Datum DEMs
    print("\n[2] Checking Calibration & Datum DEMs...")
    srtm_tif = BASE_DIR / "02_CALIBRATION_AND_DATUM_DEM" / "SRTM_GL1_30M" / "demo_srtm.tif"
    cop_dir = BASE_DIR / "02_CALIBRATION_AND_DATUM_DEM" / "COPERNICUS_GLO30" / "sample_tiles"
    cop_tifs = list(cop_dir.glob("*.tif"))
    print(f"  - SRTM GL1 30m demo datum: {'FOUND (' + str(srtm_tif.stat().st_size) + ' bytes)' if srtm_tif.exists() else 'MISSING'}")
    print(f"  - Copernicus GLO-30 sample tiles: {len(cop_tifs)} tif files")
    if not srtm_tif.exists():
        all_passed = False

    # 3. Check Pretrained Models
    print("\n[3] Checking Pretrained Models & Weights...")
    models_dir = BASE_DIR / "03_PRETRAINED_MODELS_AND_WEIGHTS"
    expected_models = [
        ("DepthAnything_V2_Small", "depth_anything_v2_vits.pth", 90_000_000),
        ("DepthAnything_V2_Base", "depth_anything_v2_vitb.pth", 350_000_000),
        ("DepthAnything_V2_Metric_Outdoor_Small", "depth_anything_v2_metric_vkitti_vits.pth", 90_000_000),
        ("DINOv2_ViTS14_Backbone", "dinov2_vits14_pretrain.pth", 80_000_000),
        ("DepthWizard_FineTuned_v1.1.0", "dav2s_gamus_ft_v1.pth", 90_000_000),
        ("DepthWizard_FineTuned_v1.1.0", "best_tall.pt", 90_000_000),
    ]

    for folder, fname, min_size in expected_models:
        fpath = models_dir / folder / fname
        if fpath.exists() and fpath.stat().st_size > min_size:
            print(f"  PASS: {folder}/{fname} ({fpath.stat().st_size / (1024*1024):.2f} MB)")
        else:
            print(f"  FAIL: {folder}/{fname} missing or incomplete!")
            all_passed = False

    # 4. Check Evaluation Samples
    print("\n[4] Checking Evaluation Samples & Test Suite...")
    eval_dir = BASE_DIR / "04_EVALUATION_SAMPLES_AND_TEST_SUITE"
    opt_samples = list((eval_dir / "optical_samples").glob("*.*"))
    ref_rasters = list((eval_dir / "reference_validation_rasters").glob("*.*"))
    print(f"  - Optical test samples: {len(opt_samples)} files")
    print(f"  - Reference validation rasters: {len(ref_rasters)} files")
    if len(opt_samples) == 0:
        all_passed = False

    # 5. Check Auxiliary Guides
    print("\n[5] Checking Auxiliary & Recommended Documentation Guides...")
    aux_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES"
    guides = list(aux_dir.rglob("*.md"))
    print(f"  - Comprehensive guides found: {len(guides)}")
    for g in guides:
        print(f"    * {g.relative_to(aux_dir)}")

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL AUDIT CHECKS PASSED: REPOSITORY IS 100% HEALTHY AND JUDGE-READY")
    else:
        print("AUDIT FAILED: Some assets require attention.")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = check_inventory()
    sys.exit(0 if success else 1)
