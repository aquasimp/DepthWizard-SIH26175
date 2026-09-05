"""DPT head and fine-tuned metric regression head."""

import torch.nn as nn


class DPTHead(nn.Module):
    """Dense Prediction Transformer head for depth/height prediction."""

    def __init__(self, in_channels: int = 64, out_channels: int = 1):
        super().__init__()
        self.head = nn.Identity()
