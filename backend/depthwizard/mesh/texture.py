"""RGB texture preparation for 3D terrain meshes."""

from pathlib import Path
from typing import Union

import cv2
import numpy as np
from PIL import Image


def nearest_power_of_two(val: int, max_dim: int = 4096) -> int:
    """Calculate the nearest power of two <= max_dim (clamped to [64, max_dim])."""
    p = 2 ** int(np.round(np.log2(max(val, 1))))
    return min(max_dim, max(64, p))


def prepare_texture(
    rgb_image: np.ndarray,
    out_path: Union[str, Path],
    max_dim: int = 4096,
    quality: int = 90,
) -> Path:
    """Resize RGB image to power-of-two <= max_dim and save as JPEG quality 90.

    Args:
        rgb_image: RGB image as uint8 numpy array (H, W, 3).
        out_path: Target path to save the JPEG texture.
        max_dim: Maximum allowed power-of-two dimension (default 4096).
        quality: JPEG compression quality (default 90).

    Returns:
        Path to the saved JPEG texture file.
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    arr = np.asarray(rgb_image)
    if arr.ndim == 2:
        # Grayscale to RGB
        arr = np.repeat(arr[:, :, None], 3, axis=-1)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        # RGBA to RGB
        arr = arr[:, :, :3]
    elif arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"Expected 3-channel RGB image, got shape {arr.shape}")

    if arr.dtype != np.uint8:
        if np.issubdtype(arr.dtype, np.floating) and np.nanmax(arr) <= 1.0:
            arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        else:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

    h, w = arr.shape[:2]
    target_w = nearest_power_of_two(w, max_dim=max_dim)
    target_h = nearest_power_of_two(h, max_dim=max_dim)

    if (w, h) != (target_w, target_h):
        interp = cv2.INTER_AREA if (target_w < w or target_h < h) else cv2.INTER_CUBIC
        resized = cv2.resize(arr, (target_w, target_h), interpolation=interp)
    else:
        resized = arr

    img = Image.fromarray(resized, mode="RGB")
    img.save(str(out_file), "JPEG", quality=quality)
    return out_file
