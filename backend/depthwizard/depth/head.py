"""DPT Head and Fine-Tuning Module for Metric nDSM."""

from pathlib import Path
from typing import Optional, Union

import torch
import torch.nn as nn

from depthwizard.depth.backbone import DepthAnythingV3Small


class DepthAnythingV3MetricHead(nn.Module):
    """Fine-tuning wrapper for Depth Anything V3 Small.

    Freezes the DINOv2 ViT-S encoder and trains the DPT decoder head
    to directly regress metric above-ground height (nDSM in metres).
    """

    def __init__(self, base_model: Optional[DepthAnythingV3Small] = None):
        super().__init__()
        if base_model is None:
            self.model = DepthAnythingV3Small()
        else:
            self.model = base_model

        # Freeze encoder completely
        self.freeze_encoder()

    def freeze_encoder(self) -> None:
        """Freeze DINOv2 encoder weights (requires_grad=False)."""
        for param in self.model.pretrained.parameters():
            param.requires_grad = False

    def unfreeze_decoder(self) -> None:
        """Ensure decoder head parameters require gradient."""
        for param in self.model.depth_head.parameters():
            param.requires_grad = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass yielding metric nDSM in metres."""
        return self.model(x)

    def save_checkpoint(self, path: Union[str, Path]) -> None:
        """Save entire model or head state dict."""
        torch.save(self.model.state_dict(), str(path))

    def load_checkpoint(self, path: Union[str, Path], device: str = "cpu") -> None:
        """Load trained metric weights."""
        state = torch.load(str(path), map_location=device, weights_only=True)
        self.model.load_state_dict(state, strict=True)
        self.model.to(device)
        self.model.eval()


# Backward compatibility alias
DepthAnythingV2MetricHead = DepthAnythingV3MetricHead
