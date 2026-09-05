"""Inference runner for Depth Anything V2 Small."""

from typing import Any

import numpy as np


def infer_image(
    model: Any,
    image_rgb: np.ndarray,
    device: str = "cpu",
    input_size: int = 518,
) -> np.ndarray:
    """Run model inference on an input RGB image."""
    h, w = image_rgb.shape[:2]
    return np.zeros((h, w), dtype=np.float32)
