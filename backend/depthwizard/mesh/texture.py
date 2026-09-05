"""RGB texture preparation for 3D terrain meshes."""

from pathlib import Path
from typing import Union

import cv2
import numpy as np
from PIL import Image


def prepare_texture(
    rgb_image: np.ndarray,
    out_path: Union[str, Path],
    max_dim: int = 4096,
    quality: int = 90,
) -> None:
    """Resize RGB to nearest power-of-two <= max_dim and save JPEG."""
    h, w = rgb_image.shape[:2]

    # Calculate nearest power of two <= max_dim
    def next_power_of_two(val: int) -> int:
        p = 1
        while p * 2 <= val and p * 2 <= max_dim:
            p *= 2
        return p

    target_w = min(max_dim, max(128, next_power_of_two(w)))
    target_h = min(max_dim, max(128, next_power_of_two(h)))

    if (w, h) != (target_w, target_h):
        resized = cv2.resize(rgb_image, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        resized = rgb_image

    img = Image.fromarray(resized)
    img.save(str(out_path), "JPEG", quality=quality)
