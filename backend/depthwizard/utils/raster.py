"""Raster utility routines."""

import numpy as np


def clean_nan_inf(arr: np.ndarray, fill_val: float = 0.0) -> np.ndarray:
    """Ensure no NaN or Inf values remain in raster."""
    out = np.copy(arr)
    invalid = ~np.isfinite(out)
    if np.any(invalid):
        out[invalid] = fill_val
    return out


def normalize_to_unit(arr: np.ndarray, p_min: float = 1.0, p_max: float = 99.0) -> np.ndarray:
    """Robust stretch array to [0, 1] using percentiles."""
    valid = np.isfinite(arr)
    if not np.any(valid):
        return np.zeros_like(arr, dtype=np.float32)

    v_min = float(np.percentile(arr[valid], p_min))
    v_max = float(np.percentile(arr[valid], p_max))
    if abs(v_max - v_min) < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)

    stretched = np.clip((arr - v_min) / (v_max - v_min), 0.0, 1.0)
    return stretched.astype(np.float32)
