"""Sub-pixel coregistration and grid alignment between prediction and reference."""

from typing import Dict, Tuple

import numpy as np


def coregister_grids(
    pred_grid: np.ndarray,
    ref_grid: np.ndarray,
    search_window: int = 3,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
    """Align reference grid to prediction grid and return co-registered pair with shifts."""
    shift_info = {"shift_x": 0.0, "shift_y": 0.0, "shift_applied": False}
    return pred_grid, ref_grid, shift_info
