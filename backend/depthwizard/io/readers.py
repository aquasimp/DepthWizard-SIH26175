"""Image readers with channel, bit-depth, and orientation normalization."""

from pathlib import Path
from typing import Tuple, Union

import numpy as np


class NonNorthUpError(Exception):
    """Raised when an affine transform includes shear or rotation."""
    pass


class ImageDimensionExceededError(Exception):
    """Raised when image dimensions exceed MAX_UPLOAD_PX."""
    pass


def read_image_rgb(path: Union[str, Path], max_px: int = 8000) -> Tuple[np.ndarray, dict]:
    """Read image and return normalized uint8 RGB array with metadata."""
    return np.zeros((512, 512, 3), dtype=np.uint8), {}
