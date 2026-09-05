"""Phase 4 Acceptance Tests: Metric nDSM head training, loss, and checkpoint loading."""

from pathlib import Path
import pytest
import torch

from depthwizard.depth.infer import DepthInferenceEngine
from training.losses import (
    MaskedL1Loss,
    MaskedSILogLoss,
    MetricNDSMLoss,
    MultiScaleGradientLoss,
)


def test_metric_losses_computation() -> None:
    """Verify SILog, L1, Grad, and combined MetricNDSMLoss compute without NaN/Inf."""
    B, H, W = 2, 64, 64
    pred = torch.full((B, 1, H, W), 15.0) + torch.randn(B, 1, H, W) * 2.0
    target = torch.full((B, 1, H, W), 15.0) + torch.randn(B, 1, H, W) * 2.0
    pred = torch.clamp(pred, min=0.0)
    target = torch.clamp(target, min=0.0)
    mask = torch.ones((B, 1, H, W), dtype=torch.bool)

    silog = MaskedSILogLoss(lambd=0.85, eps=1e-4)
    l1 = MaskedL1Loss()
    grad = MultiScaleGradientLoss(scales=3)
    composite = MetricNDSMLoss()

    l_silog = silog(pred, target, mask)
    l_l1 = l1(pred, target, mask)
    l_grad = grad(pred, target, mask)
    l_tot = composite(pred, target, mask)

    assert torch.isfinite(l_silog)
    assert l_silog.item() >= 0.0

    assert torch.isfinite(l_l1)
    assert l_l1.item() >= 0.0

    assert torch.isfinite(l_grad)
    assert l_grad.item() >= 0.0

    assert torch.isfinite(l_tot)
    assert l_tot.item() >= 0.0


def test_metric_checkpoint_loads_into_inference_engine() -> None:
    """Acceptance check 3: Exported checkpoint loads cleanly into DepthInferenceEngine(mode='metric')."""
    repo_root = Path(__file__).resolve().parent.parent
    checkpoint = repo_root / "models" / "dav2s_gamus_ft_v1.pth"
    assert checkpoint.exists(), f"Expected checkpoint at {checkpoint}"

    engine = DepthInferenceEngine(mode="metric")
    assert engine.mode == "metric"
    assert engine.model is not None


def test_training_curves_asset_exists() -> None:
    """Acceptance check 4: docs/assets/training_loss.png exists and is non-empty."""
    repo_root = Path(__file__).resolve().parent.parent
    plot_path = repo_root / "docs" / "assets" / "training_loss.png"
    assert plot_path.exists(), "Expected training_loss.png in docs/assets"
    assert plot_path.stat().st_size > 1000, "training_loss.png appears corrupt or empty"
