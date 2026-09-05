"""Sub-pixel coregistration and grid alignment between prediction and reference rasters."""

import logging
from typing import Any, Dict, Tuple

import numpy as np
import scipy.ndimage as ndi
from skimage.registration import phase_cross_correlation

logger = logging.getLogger(__name__)


def coregister_grids(
    pred_grid: np.ndarray,
    ref_grid: np.ndarray,
    search_window: int = 3,
    max_shift: float = 15.0,
    upsample_factor: int = 20,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Align reference grid to prediction grid via phase cross-correlation sub-pixel peak search.

    Args:
        pred_grid: 2D numpy array of predicted heights.
        ref_grid: 2D numpy array of reference heights.
        search_window: Radius parameter kept for API compatibility.
        max_shift: Maximum acceptable shift in pixels before flagging a warning/rejecting.
        upsample_factor: Sub-pixel resolution multiplier (e.g. 20 = 1/20th pixel resolution).

    Returns:
        Tuple of (aligned_pred, aligned_ref, shift_info)
    """
    if pred_grid.shape != ref_grid.shape:
        raise ValueError(
            f"Shape mismatch in coregistration: pred {pred_grid.shape} vs ref {ref_grid.shape}"
        )

    # Valid masks
    valid_pred = np.isfinite(pred_grid) & (pred_grid != -9999.0)
    valid_ref = np.isfinite(ref_grid) & (ref_grid != -9999.0)
    valid_common = valid_pred & valid_ref

    shift_info: Dict[str, Any] = {
        "shift_x": 0.0,
        "shift_y": 0.0,
        "shift_magnitude": 0.0,
        "shift_applied": False,
        "warning": None,
    }

    if np.sum(valid_common) < 100:
        shift_info["warning"] = "Insufficient overlapping valid pixels for coregistration."
        return pred_grid, ref_grid, shift_info

    # Prepare normalized grids for cross correlation
    p_clean = pred_grid.copy()
    r_clean = ref_grid.copy()

    p_med = float(np.median(p_clean[valid_pred]))
    r_med = float(np.median(r_clean[valid_ref]))

    p_clean[~valid_pred] = p_med
    r_clean[~valid_ref] = r_med

    # Extract gradients / edges to avoid elevation offset bias
    h, w = pred_grid.shape
    win_y = np.hanning(h)
    win_x = np.hanning(w)
    window_2d = np.outer(win_y, win_x)

    # Use Sobel gradient magnitude for edge-based correlation
    grad_p = ndi.gaussian_filter(p_clean, sigma=1.0)
    grad_r = ndi.gaussian_filter(r_clean, sigma=1.0)
    sobel_p = np.hypot(ndi.sobel(grad_p, axis=0), ndi.sobel(grad_p, axis=1)) * window_2d
    sobel_r = np.hypot(ndi.sobel(grad_r, axis=0), ndi.sobel(grad_r, axis=1)) * window_2d

    try:
        # Detected shift is vector to apply to moving_image (ref) to align with reference (pred)
        detected_shift, _, _ = phase_cross_correlation(
            reference_image=sobel_p,
            moving_image=sobel_r,
            upsample_factor=upsample_factor,
            normalization=None,
        )
        shift_y, shift_x = float(detected_shift[0]), float(detected_shift[1])
        shift_mag = float(np.hypot(shift_x, shift_y))
    except Exception as e:
        logger.warning(f"Phase cross correlation failed: {e}")
        shift_info["warning"] = f"Correlation error: {e}"
        return pred_grid, ref_grid, shift_info

    shift_info["shift_x"] = round(shift_x, 4)
    shift_info["shift_y"] = round(shift_y, 4)
    shift_info["shift_magnitude"] = round(shift_mag, 4)

    if shift_mag > max_shift:
        shift_info["warning"] = (
            f"Detected shift magnitude {shift_mag:.2f}px exceeds max threshold {max_shift}px; "
            "shift was not applied."
        )
        return pred_grid, ref_grid, shift_info

    if shift_mag > 5.0:
        shift_info["warning"] = f"Significant horizontal coregistration shift detected: {shift_mag:.2f}px"

    # If shift is smaller than 0.05px, treat as already aligned
    if shift_mag < 0.05:
        return pred_grid, ref_grid, shift_info

    # Apply sub-pixel shift to ref_grid
    aligned_ref = ndi.shift(
        ref_grid,
        shift=(shift_y, shift_x),
        order=1,
        mode="constant",
        cval=-9999.0,
    )
    shift_info["shift_applied"] = True
    return pred_grid, aligned_ref, shift_info
