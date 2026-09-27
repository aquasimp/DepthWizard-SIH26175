"""Depth Anything V3 Small model architecture and weight loading."""

from pathlib import Path
from typing import Any, Dict, List, Union

import torch
import torch.nn as nn
import torch.nn.functional as F

VITS_CONFIG: Dict[str, Any] = {
    "encoder": "vits",
    "features": 64,
    "out_channels": [48, 96, 192, 384],
}


class Attention(nn.Module):
    def __init__(self, dim: int, num_heads: int = 6):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim**-0.5
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, N, C = x.shape
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        return x


class Mlp(nn.Module):
    def __init__(self, in_features: int, hidden_features: int):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_features, bias=True)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_features, in_features, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.act(self.fc1(x)))


class Block(nn.Module):
    def __init__(self, dim: int = 384, num_heads: int = 6, mlp_ratio: float = 4.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = Attention(dim, num_heads=num_heads)
        self.ls1 = nn.Module()
        self.ls1.gamma = nn.Parameter(torch.ones(dim))
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = Mlp(dim, int(dim * mlp_ratio))
        self.ls2 = nn.Module()
        self.ls2.gamma = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.ls1.gamma * self.attn(self.norm1(x))
        x = x + self.ls2.gamma * self.mlp(self.norm2(x))
        return x


class PatchEmbed(nn.Module):
    def __init__(self, patch_size: int = 14, in_chans: int = 3, embed_dim: int = 384):
        super().__init__()
        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.proj(x).flatten(2).transpose(1, 2)


class DinoVisionTransformer(nn.Module):
    def __init__(
        self, embed_dim: int = 384, depth: int = 12, num_heads: int = 6, patch_size: int = 14
    ):
        super().__init__()
        self.patch_embed = PatchEmbed(patch_size=patch_size, in_chans=3, embed_dim=embed_dim)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, 1370, embed_dim))
        self.mask_token = nn.Parameter(torch.zeros(1, embed_dim))
        self.blocks = nn.ModuleList(
            [Block(dim=embed_dim, num_heads=num_heads) for _ in range(depth)]
        )
        self.norm = nn.LayerNorm(embed_dim)

    def interpolate_pos_encoding(self, x: torch.Tensor, w: int, h: int) -> torch.Tensor:
        npatch = x.shape[1] - 1
        N = self.pos_embed.shape[1] - 1
        if npatch == N and w == h:
            return self.pos_embed
        class_pos_embed = self.pos_embed[:, 0]
        patch_pos_embed = self.pos_embed[:, 1:]
        dim = x.shape[-1]
        w0 = w // 14
        h0 = h // 14
        M = int(N**0.5)
        patch_pos_embed = patch_pos_embed.reshape(1, M, M, dim).permute(0, 3, 1, 2)
        patch_pos_embed = F.interpolate(
            patch_pos_embed, size=(h0, w0), mode="bicubic", align_corners=False
        )
        patch_pos_embed = patch_pos_embed.permute(0, 2, 3, 1).view(1, -1, dim)
        return torch.cat((class_pos_embed.unsqueeze(0), patch_pos_embed), dim=1)

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        B, nc, h, w = x.shape
        x = self.patch_embed(x)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        x = x + self.interpolate_pos_encoding(x, w, h)

        intermediate: List[torch.Tensor] = []
        out_indices = [2, 5, 8, 11]
        for i, blk in enumerate(self.blocks):
            x = blk(x)
            if i in out_indices:
                intermediate.append(x)
        return intermediate


class ResidualConvUnit(nn.Module):
    def __init__(self, features: int):
        super().__init__()
        self.conv1 = nn.Conv2d(features, features, kernel_size=3, stride=1, padding=1, bias=True)
        self.conv2 = nn.Conv2d(features, features, kernel_size=3, stride=1, padding=1, bias=True)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.relu(x)
        out = self.conv1(out)
        out = self.relu(out)
        out = self.conv2(out)
        return out + x


class FeatureFusionBlock(nn.Module):
    def __init__(self, features: int):
        super().__init__()
        self.resConfUnit1 = ResidualConvUnit(features)
        self.resConfUnit2 = ResidualConvUnit(features)
        self.out_conv = nn.Conv2d(features, features, kernel_size=1, stride=1, padding=0, bias=True)

    def forward(self, xs: List[torch.Tensor], size: Any = None) -> torch.Tensor:
        output = xs[0]
        if len(xs) == 2:
            res = self.resConfUnit1(xs[1])
            if size is not None:
                output = F.interpolate(output, size=size, mode="bilinear", align_corners=True)
            output = output + res
        output = self.resConfUnit2(output)
        output = self.out_conv(output)
        return output


class Scratch(nn.Module):
    """Container for DPT scratch refinement layers."""

    def __init__(self, in_channels: List[int], features: int):
        super().__init__()
        self.layer1_rn = nn.Conv2d(
            in_channels[0], features, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.layer2_rn = nn.Conv2d(
            in_channels[1], features, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.layer3_rn = nn.Conv2d(
            in_channels[2], features, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.layer4_rn = nn.Conv2d(
            in_channels[3], features, kernel_size=3, stride=1, padding=1, bias=False
        )

        self.refinenet1 = FeatureFusionBlock(features)
        self.refinenet2 = FeatureFusionBlock(features)
        self.refinenet3 = FeatureFusionBlock(features)
        self.refinenet4 = FeatureFusionBlock(features)

        self.output_conv1 = nn.Conv2d(features, features // 2, kernel_size=3, stride=1, padding=1)
        self.output_conv2 = nn.Sequential(
            nn.Conv2d(features // 2, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(True),
            nn.Conv2d(32, 1, kernel_size=1, stride=1, padding=0),
            nn.ReLU(True),
        )


class DPTHead(nn.Module):
    def __init__(
        self,
        in_channels: int = 384,
        features: int = 64,
        out_channels: Any = None,
    ):
        super().__init__()
        channels = out_channels if out_channels is not None else [48, 96, 192, 384]
        self.projects = nn.ModuleList(
            [
                nn.Conv2d(in_channels, channels[0], kernel_size=1, bias=True),
                nn.Conv2d(in_channels, channels[1], kernel_size=1, bias=True),
                nn.Conv2d(in_channels, channels[2], kernel_size=1, bias=True),
                nn.Conv2d(in_channels, channels[3], kernel_size=1, bias=True),
            ]
        )
        self.resize_layers = nn.ModuleList(
            [
                nn.ConvTranspose2d(channels[0], channels[0], kernel_size=4, stride=4, padding=0),
                nn.ConvTranspose2d(channels[1], channels[1], kernel_size=2, stride=2, padding=0),
                nn.Identity(),
                nn.Conv2d(channels[3], channels[3], kernel_size=3, stride=2, padding=1),
            ]
        )
        self.scratch = Scratch(channels, features)

    def forward(self, out_features: List[torch.Tensor], patch_h: int, patch_w: int) -> torch.Tensor:
        out: List[torch.Tensor] = []
        for i, x in enumerate(out_features):
            x = x[:, 1:].permute(0, 2, 1).reshape((x.shape[0], x.shape[-1], patch_h, patch_w))
            x = self.projects[i](x)
            x = self.resize_layers[i](x)
            out.append(x)

        layer_1, layer_2, layer_3, layer_4 = out
        layer_1_rn = self.scratch.layer1_rn(layer_1)
        layer_2_rn = self.scratch.layer2_rn(layer_2)
        layer_3_rn = self.scratch.layer3_rn(layer_3)
        layer_4_rn = self.scratch.layer4_rn(layer_4)

        path_4 = self.scratch.refinenet4([layer_4_rn])
        path_3 = self.scratch.refinenet3([path_4, layer_3_rn], size=layer_3_rn.shape[2:])
        path_2 = self.scratch.refinenet2([path_3, layer_2_rn], size=layer_2_rn.shape[2:])
        path_1 = self.scratch.refinenet1([path_2, layer_1_rn], size=layer_1_rn.shape[2:])

        out_conv1 = self.scratch.output_conv1(path_1)
        out_interp = F.interpolate(
            out_conv1, (patch_h * 14, patch_w * 14), mode="bilinear", align_corners=True
        )
        return self.scratch.output_conv2(out_interp)


class DepthAnythingV3Small(nn.Module):
    """Depth Anything V3 Small complete model."""

    def __init__(self, encoder: str = "vits", features: int = 64, out_channels: Any = None):
        super().__init__()
        self.pretrained = DinoVisionTransformer()
        self.depth_head = DPTHead(
            in_channels=384,
            features=features,
            out_channels=out_channels or [48, 96, 192, 384],
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h, w = x.shape[-2:]
        patch_h, patch_w = h // 14, w // 14
        features = self.pretrained(x)
        depth = self.depth_head(features, patch_h, patch_w)
        return depth


# Backward compatibility alias
DepthAnythingV2Small = DepthAnythingV3Small


def load_dav3_small(checkpoint_path: Union[str, Path], device: str = "cpu") -> DepthAnythingV3Small:
    """Load Depth Anything V3 Small model with exact strict matching."""
    model = DepthAnythingV3Small(**VITS_CONFIG)
    p = Path(checkpoint_path)
    if not p.exists():
        # Check alternative naming fallbacks
        alt_str = str(checkpoint_path).replace("depth_anything_v3", "depth_anything_v2").replace("dav3s", "dav2s")
        if Path(alt_str).exists():
            p = Path(alt_str)
        else:
            alt_v3 = str(checkpoint_path).replace("depth_anything_v2", "depth_anything_v3").replace("dav2s", "dav3s")
            if Path(alt_v3).exists():
                p = Path(alt_v3)
    state = torch.load(str(p), map_location=device, weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()
    return model


# Backward compatibility alias
load_dav2_small = load_dav3_small
