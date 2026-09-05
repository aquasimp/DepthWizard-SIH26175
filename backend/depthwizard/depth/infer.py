"""Inference engine for Depth Anything V2 Small with seamless tiling."""

import time
from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from depthwizard.depth.backbone import DepthAnythingV2Small, load_dav2_small
from depthwizard.depth.tiling import infer_tiled
from depthwizard.utils.logging import logger

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)


class DepthInferenceEngine:
    """Manages Depth Anything V2 inference over full scenes and sliding tiles."""

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = "models/depth_anything_v2_vits.pth",
        device: str = "auto",
    ):
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(
            "Initializing DepthInferenceEngine",
            extra={"device": self.device, "checkpoint": str(checkpoint_path)},
        )
        self.model: DepthAnythingV2Small = load_dav2_small(checkpoint_path, device=self.device)

    def infer_tile(self, tile_rgb: np.ndarray, input_size: int = 518) -> np.ndarray:
        """Infer depth for a single square tile.

        Args:
            tile_rgb: (H, W, 3) uint8 or float32 image.
            input_size: Model input resolution (default 518).
        """
        orig_h, orig_w = tile_rgb.shape[:2]

        # Convert to float in [0, 1]
        if tile_rgb.dtype == np.uint8:
            img = tile_rgb.astype(np.float32) / 255.0
        else:
            img = tile_rgb.astype(np.float32)
            if img.max() > 1.0:
                img = img / 255.0

        # Resize to input_size
        if (orig_h, orig_w) != (input_size, input_size):
            img_resized = cv2.resize(img, (input_size, input_size), interpolation=cv2.INTER_CUBIC)
        else:
            img_resized = img

        # Normalize with ImageNet stats
        norm = ((img_resized - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)
        tensor = torch.from_numpy(norm).unsqueeze(0).to(self.device).float()

        with torch.no_grad():
            pred = self.model(tensor)  # (1, 1, input_size, input_size)

        # Resize back to original tile size if necessary
        if (orig_h, orig_w) != (input_size, input_size):
            pred = F.interpolate(pred, size=(orig_h, orig_w), mode="bilinear", align_corners=True)

        depth = pred.squeeze().cpu().numpy().astype(np.float32)
        return depth

    def infer_scene(
        self,
        image_rgb: np.ndarray,
        tile_size: int = 512,
        overlap: int = 64,
    ) -> Tuple[np.ndarray, float]:
        """Run inference over full image using seamless tiling and measure wall time."""
        start_time = time.perf_counter()

        def tile_fn(tile: np.ndarray) -> np.ndarray:
            return self.infer_tile(tile, input_size=518)

        depth = infer_tiled(tile_fn, image_rgb, tile_size=tile_size, overlap=overlap)
        wall_time = time.perf_counter() - start_time

        logger.info(
            "Completed scene depth inference",
            extra={
                "shape": list(image_rgb.shape[:2]),
                "wall_time_seconds": round(wall_time, 3),
                "device": self.device,
            },
        )
        return depth, wall_time


def colorize_depth(
    depth: np.ndarray,
    colormap: int = cv2.COLORMAP_INFERNO,
    invert: bool = False,
) -> np.ndarray:
    """Colorize a float depth map to uint8 RGB."""
    valid = np.isfinite(depth)
    if not np.any(valid):
        return np.zeros((*depth.shape, 3), dtype=np.uint8)

    d_min = float(np.percentile(depth[valid], 1))
    d_max = float(np.percentile(depth[valid], 99))
    if abs(d_max - d_min) < 1e-6:
        norm_uint8 = np.zeros_like(depth, dtype=np.uint8)
    else:
        norm_float = np.clip((depth - d_min) / (d_max - d_min), 0.0, 1.0)
        if invert:
            norm_float = 1.0 - norm_float
        norm_uint8 = (norm_float * 255.0).astype(np.uint8)

    colored = cv2.applyColorMap(norm_uint8, colormap)
    return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
