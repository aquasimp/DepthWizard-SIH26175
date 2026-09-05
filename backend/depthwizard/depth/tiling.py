"""Seamless tiled inference with cosine-feathered blending and overlap median matching."""

from typing import Callable, List, Tuple

import numpy as np


def compute_tile_weight(
    tile_size: int,
    overlap: int,
    is_top: bool,
    is_bottom: bool,
    is_left: bool,
    is_right: bool,
) -> np.ndarray:
    """Compute 2D cosine-feathered blending weight map for a tile."""
    # 1D weights along height
    w_y = np.ones(tile_size, dtype=np.float32)
    ramp = 0.5 * (1.0 - np.cos(np.pi * (np.arange(overlap, dtype=np.float32) + 0.5) / overlap))
    if not is_top:
        w_y[:overlap] = ramp
    if not is_bottom:
        w_y[-overlap:] = ramp[::-1]

    # 1D weights along width
    w_x = np.ones(tile_size, dtype=np.float32)
    if not is_left:
        w_x[:overlap] = ramp
    if not is_right:
        w_x[-overlap:] = ramp[::-1]

    return np.outer(w_y, w_x)


def get_tile_coordinates(
    img_h: int,
    img_w: int,
    tile_size: int = 512,
    overlap: int = 64,
) -> List[Tuple[int, int, bool, bool, bool, bool]]:
    """Compute top-left coordinates and boundary flags for sliding window tiles."""
    stride = tile_size - overlap
    coords: List[Tuple[int, int, bool, bool, bool, bool]] = []

    # Row offsets
    r_offsets: List[int] = []
    r = 0
    while r + tile_size < img_h:
        r_offsets.append(r)
        r += stride
    r_offsets.append(max(0, img_h - tile_size))
    # Deduplicate while preserving order
    r_offsets = sorted(list(set(r_offsets)))

    # Column offsets
    c_offsets: List[int] = []
    c = 0
    while c + tile_size < img_w:
        c_offsets.append(c)
        c += stride
    c_offsets.append(max(0, img_w - tile_size))
    c_offsets = sorted(list(set(c_offsets)))

    for r_idx, r_pos in enumerate(r_offsets):
        for c_idx, c_pos in enumerate(c_offsets):
            is_top = (r_idx == 0)
            is_bottom = (r_idx == len(r_offsets) - 1)
            is_left = (c_idx == 0)
            is_right = (c_idx == len(c_offsets) - 1)
            coords.append((r_pos, c_pos, is_top, is_bottom, is_left, is_right))

    return coords


def infer_tiled(
    infer_fn: Callable[[np.ndarray], np.ndarray],
    image: np.ndarray,
    tile_size: int = 512,
    overlap: int = 64,
) -> np.ndarray:
    """Execute seamless tiled inference with cosine-feathered blending and median alignment.

    Args:
        infer_fn: Function mapping (tile_h, tile_w, 3) uint8/float32 RGB to (tile_h, tile_w) float32 depth.
        image: Input RGB image of shape (H, W, 3).
        tile_size: Square tile dimension (default 512).
        overlap: Overlap in pixels between adjacent tiles (default 64).

    Returns:
        Full-resolution blended depth map of shape (H, W).
    """
    H, W = image.shape[:2]

    # If image is smaller than or equal to tile_size in both dimensions, infer directly
    if H <= tile_size and W <= tile_size:
        return infer_fn(image)

    accum_depth = np.zeros((H, W), dtype=np.float32)
    accum_weight = np.zeros((H, W), dtype=np.float32)

    tile_coords = get_tile_coordinates(H, W, tile_size=tile_size, overlap=overlap)

    for r, c, is_top, is_bottom, is_left, is_right in tile_coords:
        tile_img = image[r : r + tile_size, c : c + tile_size]
        tile_pred = infer_fn(tile_img)

        # Compute overlap with previously accumulated predictions
        existing_w = accum_weight[r : r + tile_size, c : c + tile_size]
        overlap_mask = existing_w > 1e-4

        # Median matching: align tile offset to current accumulator in overlap region
        if np.sum(overlap_mask) >= 64:
            existing_d = accum_depth[r : r + tile_size, c : c + tile_size][overlap_mask] / existing_w[overlap_mask]
            new_d = tile_pred[overlap_mask]
            delta = float(np.median(existing_d - new_d))
            tile_pred = tile_pred + delta

        # Compute cosine blending weights
        weight = compute_tile_weight(
            tile_size=tile_size,
            overlap=overlap,
            is_top=is_top,
            is_bottom=is_bottom,
            is_left=is_left,
            is_right=is_right,
        )

        accum_depth[r : r + tile_size, c : c + tile_size] += tile_pred * weight
        accum_weight[r : r + tile_size, c : c + tile_size] += weight

    valid_mask = accum_weight > 1e-6
    blended = np.zeros((H, W), dtype=np.float32)
    blended[valid_mask] = accum_depth[valid_mask] / accum_weight[valid_mask]

    return blended
