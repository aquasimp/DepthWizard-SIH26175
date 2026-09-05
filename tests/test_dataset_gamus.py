"""Phase 1 Acceptance Tests: GAMUS Dataset Loader, batch shapes, scaling, manifest, sample data."""

import csv
from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import DataLoader

from training.dataset import GAMUSDataset


def test_samples_contain_required_variants() -> None:
    """data/samples/ must contain:
    1. Georeferenced GeoTIFF with CRS + affine transform
    2. Plain PNG (non-georeferenced)
    3. TIFF without CRS
    """
    samples_dir = Path("data/samples")
    assert samples_dir.exists(), "data/samples directory does not exist"

    # 1. Georeferenced GeoTIFF
    georef_files = []
    plain_png_files = []
    unref_tiff_files = []

    for p in samples_dir.glob("*"):
        if p.suffix.lower() == ".png":
            plain_png_files.append(p)
        elif p.suffix.lower() in [".tif", ".tiff"]:
            try:
                with rasterio.open(str(p)) as src:
                    if (
                        src.crs is not None
                        and src.transform is not None
                        and not src.transform.is_identity
                    ):
                        georef_files.append(p)
                    else:
                        unref_tiff_files.append(p)
            except Exception:
                pass

    assert len(georef_files) >= 1, (
        f"Expected at least 1 georeferenced GeoTIFF, found {len(georef_files)}"
    )
    assert len(plain_png_files) >= 1, f"Expected at least 1 plain PNG, found {len(plain_png_files)}"
    assert len(unref_tiff_files) >= 1, (
        f"Expected at least 1 TIFF without CRS, found {len(unref_tiff_files)}"
    )


def test_manifest_csv_matches_files_on_disk() -> None:
    """Verify manifest CSV row count exactly matches files present on disk."""
    manifest_path = Path("data/gamus/manifest.csv")
    assert manifest_path.exists(), f"Manifest missing at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0, "Manifest contains 0 rows"

    disk_files_count = 0
    for split in ["train", "val"]:
        split_dir = Path("data/gamus") / split
        if split_dir.exists():
            disk_files_count += len(list(split_dir.glob("*.npz")))

    assert len(rows) == disk_files_count, (
        f"Manifest rows ({len(rows)}) do not match disk npz count ({disk_files_count})"
    )


def test_gamus_dataloader_batch_shapes_and_metric_scale() -> None:
    """Acceptance criteria:
    - a DataLoader batch has shapes (B,3,518,518) and (B,1,518,518), dtype float32
    - assert the nDSM 99th percentile across a sampled batch lies in [10, 80] metres
      (catches unit and scaling errors immediately - fail loudly if not)
    """
    manifest_path = Path("data/gamus/manifest.csv")
    dataset = GAMUSDataset(manifest_path=manifest_path, split="train", crop_size=518, augment=False)
    assert len(dataset) > 0, "GAMUS train dataset is empty"

    batch_size = 4
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    batch = next(iter(loader))

    image = batch["image"]
    depth = batch["depth"]
    mask = batch["mask"]

    # Check shapes
    assert image.shape == (batch_size, 3, 518, 518), f"Unexpected image shape: {image.shape}"
    assert depth.shape == (batch_size, 1, 518, 518), f"Unexpected depth shape: {depth.shape}"
    assert mask.shape == (batch_size, 1, 518, 518), f"Unexpected mask shape: {mask.shape}"

    # Check dtypes
    assert image.dtype == torch.float32, f"Expected float32 image, got {image.dtype}"
    assert depth.dtype == torch.float32, f"Expected float32 depth, got {depth.dtype}"
    assert mask.dtype == torch.bool, f"Expected bool mask, got {mask.dtype}"

    # Check metric scaling: 99th percentile across sampled batch must lie in [10, 80] metres
    valid_depths = depth[mask].cpu().numpy()
    assert len(valid_depths) > 0, "No valid depth pixels in sampled batch"
    p99 = float(np.percentile(valid_depths, 99))
    print(f"Sampled batch nDSM 99th percentile: {p99:.2f} m")

    assert 10.0 <= p99 <= 80.0, (
        f"nDSM 99th percentile ({p99:.2f} m) is outside expected metric range [10, 80] metres!"
    )


def test_augmentation_spatial_alignment_and_value_invariance() -> None:
    """Step 8 / Mutation D: Verify geometric augmentation invariance across all 8 rotation/flip combinations.

    Asserts:
    1. height.min() and height.max() are IDENTICAL before and after (no negation, no value flip).
    2. Pixel position of image maximum coincides with height maximum after the transform.
    3. Detecting deliberate misalignment (e.g. k vs k+1) immediately causes a failure.
    """
    from training.dataset import apply_geometric_augmentations

    H, W = 100, 100
    # Pure row ramp: height[r, c] = r
    r_ramp = np.arange(H, dtype=np.float32)[:, None] * np.ones((1, W), dtype=np.float32)

    img_orig = np.zeros((H, W, 3), dtype=np.uint8)
    img_orig[:, :, 0] = (r_ramp / (H - 1) * 255.0).astype(np.uint8)
    hgt_orig = r_ramp.copy()
    mask_orig = np.ones((H, W), dtype=bool)

    # 4 rotations x 2 flip_lr x 2 flip_ud = 16 combinations
    for k in [0, 1, 2, 3]:
        for flip_lr in [False, True]:
            for flip_ud in [False, True]:
                img_aug, hgt_aug, _ = apply_geometric_augmentations(
                    img_orig.copy(), hgt_orig.copy(), mask_orig.copy(),
                    k=k, flip_lr=flip_lr, flip_ud=flip_ud,
                )

                # (a) Values must remain identical: no negation, no inversion
                assert hgt_aug.min() == hgt_orig.min(), f"Min value changed under k={k}, lr={flip_lr}, ud={flip_ud}"
                assert hgt_aug.max() == hgt_orig.max(), f"Max value changed under k={k}, lr={flip_lr}, ud={flip_ud}"
                assert hgt_aug.mean() == hgt_orig.mean(), f"Mean value changed under k={k}, lr={flip_lr}, ud={flip_ud}"

                # (b) Spatial alignment: image peak must coincide with height peak
                img_peak = np.unravel_index(np.argmax(img_aug[:, :, 0]), (H, W))
                hgt_peak = np.unravel_index(np.argmax(hgt_aug), (H, W))
                assert img_peak == hgt_peak, (
                    f"Spatial misalignment in augmentation (k={k}, lr={flip_lr}, ud={flip_ud}): "
                    f"img_peak={img_peak} != hgt_peak={hgt_peak}"
                )

    # Also verify loader runs cleanly with augment=True
    manifest_path = Path("data/gamus/manifest.csv")
    aug_dataset = GAMUSDataset(manifest_path=manifest_path, split="train", crop_size=518, augment=True)
    sample = aug_dataset[0]
    assert sample["image"].shape == (3, 518, 518)
    assert sample["depth"].shape == (1, 518, 518)
    assert torch.all(sample["depth"] >= 0.0)
