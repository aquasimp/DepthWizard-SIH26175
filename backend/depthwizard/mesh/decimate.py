"""Multi-resolution LOD generation using proper area-averaging decimation."""

from typing import Dict, Tuple

import cv2
import numpy as np

LOD_RESOLUTIONS: Dict[str, Tuple[int, int]] = {
    "lod0": (512, 512),
    "lod1": (256, 256),
    "lod2": (128, 128),
}


def decimate_heightmap(
    heightmap: np.ndarray,
    target_shape: Tuple[int, int] = (512, 512),
) -> np.ndarray:
    """Downsample heightmap using INTER_AREA to prevent edge spiking."""
    h_tgt, w_tgt = target_shape
    return cv2.resize(heightmap, (w_tgt, h_tgt), interpolation=cv2.INTER_AREA)
