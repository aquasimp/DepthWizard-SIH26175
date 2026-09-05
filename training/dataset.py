"""PyTorch Dataset for GAMUS paired RGB and metric nDSM tiles."""

from typing import Dict, List

import numpy as np
import torch
from torch.utils.data import Dataset

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)


class GAMUSDataset(Dataset):
    """GAMUS Paired RGB and Metric nDSM Dataset."""

    def __init__(
        self,
        samples: List[Dict[str, str]],
        crop_size: int = 518,
        augment: bool = False,
    ):
        self.samples = samples
        self.crop_size = crop_size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        # Stub implementation yielding correctly shaped tensors
        rgb = np.zeros((3, self.crop_size, self.crop_size), dtype=np.float32)
        ndsm = np.zeros((1, self.crop_size, self.crop_size), dtype=np.float32)
        mask = np.ones((1, self.crop_size, self.crop_size), dtype=bool)

        return {
            "image": torch.from_numpy(rgb),
            "depth": torch.from_numpy(ndsm),
            "mask": torch.from_numpy(mask),
        }
