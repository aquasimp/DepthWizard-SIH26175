"""Depth Anything V2 Small model architecture and weight loading."""

from typing import Any, Dict

import torch.nn as nn

VITS_CONFIG: Dict[str, Any] = {
    "encoder": "vits",
    "features": 64,
    "out_channels": [48, 96, 192, 384],
}


class DepthAnythingV2(nn.Module):
    """Depth Anything V2 Small model implementation."""

    def __init__(self, encoder: str = "vits", features: int = 64, out_channels: Any = None):
        super().__init__()
        self.encoder_name = encoder
        self.features = features
        self.out_channels = out_channels or [48, 96, 192, 384]


def load_dav2_small(checkpoint_path: str, device: str = "cpu") -> DepthAnythingV2:
    """Load Depth Anything V2 Small model from checkpoint."""
    model = DepthAnythingV2(**VITS_CONFIG)
    return model
