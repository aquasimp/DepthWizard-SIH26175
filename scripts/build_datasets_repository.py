"""Populate and structure X:\\DatasetsSIH 26175 with all required and recommended resources."""

import os
import json
import shutil
from pathlib import Path

target_root = Path("X:/DatasetsSIH 26175")
target_root.mkdir(parents=True, exist_ok=True)
repo_root = Path(__file__).resolve().parent.parent

print(f"Building complete dataset repository at: {target_root}")

# -----------------------------------------------------------------------------
# 1. PRIMARY BENCHMARK: GAMUS
# -----------------------------------------------------------------------------
gamus_dir = target_root / "01_REQUIRED_PRIMARY_BENCHMARK" / "GAMUS"
gamus_meta_dir = gamus_dir / "metadata"
gamus_raw_img_dir = gamus_dir / "raw_h5" / "images"
gamus_raw_agl_dir = gamus_dir / "raw_h5" / "heights"
gamus_raw_cls_dir = gamus_dir / "raw_h5" / "classes"
gamus_npz_train_dir = gamus_dir / "npz_canonical_crops" / "train"
gamus_npz_val_dir = gamus_dir / "npz_canonical_crops" / "val"
gamus_npz_test_dir = gamus_dir / "npz_canonical_crops" / "test"

for d in [gamus_meta_dir, gamus_raw_img_dir, gamus_raw_agl_dir, gamus_raw_cls_dir, 
          gamus_npz_train_dir, gamus_npz_val_dir, gamus_npz_test_dir]:
    d.mkdir(parents=True, exist_ok=True)

# Copy Metadata
print("Copying GAMUS metadata...")
for src_name, dst_name in [
    ("artifacts/v1.1.0/hf_inventory.json", "hf_inventory.json"),
    ("artifacts/v1.1.0/hf_file_list.txt", "hf_file_list.txt"),
    ("data/gamus/manifest.csv", "gamus_manifest.csv"),
    ("data/gamus/smoke_manifest_v110.csv", "smoke_manifest_v110.csv"),
]:
    src = repo_root / src_name
    if src.exists():
        shutil.copy2(src, gamus_meta_dir / dst_name)

# Link representative raw HDF5 files from data/gamus_raw
print("Linking representative raw HDF5 files...")
raw_root = repo_root / "data" / "gamus_raw"
if raw_root.exists():
    for mod, dst_sub in [("images", gamus_raw_img_dir), ("heights", gamus_raw_agl_dir), ("classes", gamus_raw_cls_dir)]:
        mod_dir = raw_root / mod
        if mod_dir.exists():
            count = 0
            for split_dir in mod_dir.iterdir():
                if split_dir.is_dir():
                    target_split = dst_sub / split_dir.name
                    target_split.mkdir(parents=True, exist_ok=True)
                    # Pick top representative files per city
                    for h5 in split_dir.glob("*.h5"):
                        dst_file = target_split / h5.name
                        if not dst_file.exists():
                            try:
                                os.link(h5, dst_file)
                                count += 1
                            except Exception:
                                shutil.copy2(h5, dst_file)
                                count += 1
            print(f"  Linked {count} {mod} HDF5 files.")

# Link canonical npz crops (train, val, test)
print("Linking canonical npz crops...")
gamus_npz_root = repo_root / "data" / "gamus"
for split, dst_split in [("train", gamus_npz_train_dir), ("val", gamus_npz_val_dir), ("test", gamus_npz_test_dir)]:
    src_split = gamus_npz_root / split
    if src_split.exists():
        count = 0
        for npz in src_split.glob("*.npz"):
            dst_file = dst_split / npz.name
            if not dst_file.exists():
                try:
                    os.link(npz, dst_file)
                    count += 1
                except Exception:
                    shutil.copy2(npz, dst_file)
                    count += 1
        print(f"  Linked {count} {split} .npz crops.")

# -----------------------------------------------------------------------------
# 2. CALIBRATION & DATUM DEM
# -----------------------------------------------------------------------------
calib_dir = target_root / "02_CALIBRATION_AND_DATUM_DEM"
srtm_dir = calib_dir / "SRTM_GL1_30M"
cop_dir = calib_dir / "COPERNICUS_GLO30"
srtm_dir.mkdir(parents=True, exist_ok=True)
cop_dir.mkdir(parents=True, exist_ok=True)

# Link demo SRTM tile
demo_srtm = repo_root / "data" / "cache" / "srtm" / "demo_srtm.tif"
if demo_srtm.exists():
    dst = srtm_dir / "demo_srtm.tif"
    if not dst.exists():
        try:
            os.link(demo_srtm, dst)
        except Exception:
            shutil.copy2(demo_srtm, dst)
    print("Linked demo_srtm.tif to SRTM_GL1_30M.")

# -----------------------------------------------------------------------------
# 3. EVALUATION SAMPLES & TEST SUITE
# -----------------------------------------------------------------------------
eval_dir = target_root / "04_EVALUATION_SAMPLES_AND_TEST_SUITE"
optical_dir = eval_dir / "optical_samples"
ref_dir = eval_dir / "reference_validation_rasters"
optical_dir.mkdir(parents=True, exist_ok=True)
ref_dir.mkdir(parents=True, exist_ok=True)

samples_src = repo_root / "data" / "samples"
for sample_file in samples_src.glob("*.*"):
    if sample_file.is_file() and not sample_file.name.startswith("."):
        dst = optical_dir / sample_file.name
        if not dst.exists():
            try:
                os.link(sample_file, dst)
            except Exception:
                shutil.copy2(sample_file, dst)
print("Linked optical sample imagery.")

diff_raster = repo_root / "outputs" / "evaluation" / "signed_difference_ndsm.tif"
if diff_raster.exists():
    dst = ref_dir / "signed_difference_ndsm.tif"
    if not dst.exists():
        try:
            os.link(diff_raster, dst)
        except Exception:
            shutil.copy2(diff_raster, dst)
    print("Linked signed_difference_ndsm.tif.")

print("Base files linked and organized successfully.")
