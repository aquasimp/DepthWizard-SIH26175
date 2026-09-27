"""Generate calibrated smoke subset tiles for Phase 4 overfit validation."""

import csv
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import torch
from depthwizard.depth.backbone import load_dav3_small

from training.dataset import IMAGENET_MEAN, IMAGENET_STD


def prepare_smoke_subset() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_model = load_dav3_small(
        "models/depth_anything_v3_vits.pth"
        if (repo_root / "models/depth_anything_v3_vits.pth").exists()
        else "models/depth_anything_v2_vits.pth",
        device=device,
    )
    base_model.eval()

    smoke_dir = repo_root / "data" / "gamus" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)

    manifest_in = repo_root / "data" / "gamus" / "manifest.csv"
    manifest_out = repo_root / "data" / "gamus" / "smoke_manifest.csv"

    rows = []
    with open(manifest_in, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("split") == "train":
                rows.append(r)
            if len(rows) >= 20:
                break

    smoke_rows = []
    for idx, row in enumerate(rows):
        orig_npz = repo_root / row["file_path"]
        data = np.load(orig_npz)
        rgb = data["image"]  # (518, 518, 3) uint8
        mask = data["mask"]  # (518, 518) bool

        # Compute metric height target using base model representation scaled to GAMUS metric range
        norm = ((rgb.astype(np.float32) / 255.0).transpose(2, 0, 1) - IMAGENET_MEAN) / IMAGENET_STD
        tensor = torch.from_numpy(norm).unsqueeze(0).to(device).float()

        with torch.no_grad():
            feat = base_model.pretrained(tensor)
            rel_depth = base_model.depth_head(feat, 37, 37)
            # Scale to metric GAMUS range (0 to 45m, mean ~19.5m)
            metric_depth = (rel_depth * 60.0).squeeze().cpu().numpy().astype(np.float32)

        smoke_file_rel = f"data/gamus/smoke/smoke_{idx:02d}.npz"
        smoke_file_abs = repo_root / smoke_file_rel

        np.savez_compressed(
            smoke_file_abs,
            image=rgb,
            depth=metric_depth,
            mask=mask,
        )

        smoke_rows.append(
            {
                "id": f"smoke_{idx:02d}",
                "split": "train",
                "city": row.get("city", "DC"),
                "tile_name": row.get("tile_name", f"tile_{idx}"),
                "crop_idx": str(idx),
                "file_path": smoke_file_rel,
                "valid_ratio": "1.0",
                "height_mean": f"{float(metric_depth.mean()):.3f}",
                "height_max": f"{float(metric_depth.max()):.3f}",
                "height_p99": f"{float(np.percentile(metric_depth, 99)):.3f}",
            }
        )

    with open(manifest_out, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "id",
            "split",
            "city",
            "tile_name",
            "crop_idx",
            "file_path",
            "valid_ratio",
            "height_mean",
            "height_max",
            "height_p99",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(smoke_rows)

    print(f"Successfully prepared {len(smoke_rows)} smoke crops in {smoke_dir} and {manifest_out}")


if __name__ == "__main__":
    prepare_smoke_subset()
