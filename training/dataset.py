"""PyTorch Dataset for GAMUS paired RGB and metric nDSM crops."""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import torch
from torch.utils.data import Dataset

# Canonical ImageNet normalization statistics
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)


class GAMUSDataset(Dataset):
    """GAMUS Paired RGB and Metric nDSM Dataset."""

    def __init__(
        self,
        manifest_path: Union[str, Path],
        split: Optional[str] = None,
        crop_size: int = 518,
        augment: bool = False,
    ):
        self.manifest_path = Path(manifest_path)
        self.crop_size = crop_size
        self.augment = augment
        self.repo_root = self.manifest_path.parent.parent.parent

        self.samples: List[Dict[str, str]] = []
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if split is None or row.get("split") == split:
                        self.samples.append(row)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        row = self.samples[idx]
        file_rel = row["file_path"]
        file_path = self.repo_root / file_rel

        data = np.load(file_path)
        rgb = data["image"]  # uint8 (518, 518, 3)
        ndsm = data["depth"]  # float32 (518, 518) in metres
        mask = data["mask"]  # bool (518, 518)

        # Ensure shapes
        if rgb.shape[0] != self.crop_size or rgb.shape[1] != self.crop_size:
            rgb = rgb[: self.crop_size, : self.crop_size]
            ndsm = ndsm[: self.crop_size, : self.crop_size]
            mask = mask[: self.crop_size, : self.crop_size]

        # Geometry-preserving augmentations: rotations in {0, 90, 180, 270} and flips
        # CRITICAL: rotate/flip spatial dimensions TOGETHER.
        # NEVER negate or invert height values!
        # NEVER apply photometric jitter that modifies shadow directions!
        if self.augment:
            k = np.random.choice([0, 1, 2, 3])
            if k > 0:
                rgb = np.rot90(rgb, k=k, axes=(0, 1)).copy()
                ndsm = np.rot90(ndsm, k=k, axes=(0, 1)).copy()
                mask = np.rot90(mask, k=k, axes=(0, 1)).copy()

            if np.random.rand() > 0.5:
                # Horizontal flip
                rgb = np.fliplr(rgb).copy()
                ndsm = np.fliplr(ndsm).copy()
                mask = np.fliplr(mask).copy()

            if np.random.rand() > 0.5:
                # Vertical flip (spatial coordinates only, never values)
                rgb = np.flipud(rgb).copy()
                ndsm = np.flipud(ndsm).copy()
                mask = np.flipud(mask).copy()

        # Normalize RGB to [0, 1] then ImageNet standard stats -> (3, H, W)
        rgb_float = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)
        rgb_norm = (rgb_float - IMAGENET_MEAN) / IMAGENET_STD

        # nDSM remains strictly in metric units (metres above ground level) -> (1, H, W)
        ndsm_tensor = ndsm[np.newaxis, :, :].astype(np.float32)
        mask_tensor = mask[np.newaxis, :, :].astype(bool)

        return {
            "image": torch.from_numpy(rgb_norm),
            "depth": torch.from_numpy(ndsm_tensor),
            "mask": torch.from_numpy(mask_tensor),
        }
