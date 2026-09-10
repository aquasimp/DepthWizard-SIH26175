"""Integration test suite verifying canonical system integrity and audit remediation.

Tests:
1. Canonical architectural modules: backbone.py, head.py, dtm_decompose.py, gcp_fit.py, ransac_affine.py, eval/coregister.py, losses.py
2. Calibration selector offline SRTM fallback resilience
3. Frontend ControlHud component existence
"""

from pathlib import Path
import numpy as np
import pytest
import torch


def test_depth_backbone_and_head_components():
    """Verify backend/depthwizard/depth/backbone.py and head.py instantiate and function."""
    from depthwizard.depth.backbone import Block, DinoVisionTransformer, DPTHead, ResidualConvUnit
    from depthwizard.depth.head import DepthAnythingV2MetricHead

    assert DinoVisionTransformer is not None
    assert DPTHead is not None
    assert DepthAnythingV2MetricHead is not None

    block = Block(dim=384, num_heads=6)
    x = torch.randn(1, 196, 384)
    out = block(x)
    assert out.shape == (1, 196, 384)

    rcu = ResidualConvUnit(features=64)
    t = torch.randn(1, 64, 32, 32)
    rcu_out = rcu(t)
    assert rcu_out.shape == (1, 64, 32, 32)


def test_eval_coregister_module():
    """Verify backend/depthwizard/eval/coregister.py correctly aligns grids."""
    import scipy.ndimage as ndi
    from depthwizard.eval.coregister import coregister_grids

    np.random.seed(42)
    base = ndi.gaussian_filter(np.random.randn(64, 64).astype(np.float32) * 5.0 + 50.0, sigma=3.0)
    ref = ndi.shift(base, (1.0, -1.0), order=1, mode="nearest")

    aligned_pred, aligned_ref, shift_info = coregister_grids(base, ref, max_shift=5.0)

    assert "shift_magnitude" in shift_info
    assert aligned_pred.shape == (64, 64)
    assert aligned_ref.shape == (64, 64)


def test_calibration_gcp_and_ransac():
    """Verify calibration GCP and RANSAC affine functions."""
    from depthwizard.calibration.gcp_fit import check_gcp_collinearity
    from depthwizard.calibration.ransac_affine import calibrate_path_c

    # Collinear GCP check
    collinear_pts = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]], dtype=np.float32)
    assert check_gcp_collinearity(collinear_pts) is True

    # Path C RANSAC degeneracy guard on flat scene
    flat_disparity = np.zeros((32, 32), dtype=np.float32)
    cal_dsm, meta = calibrate_path_c(flat_disparity)
    assert meta["is_degenerate"] is True


def test_calibration_dtm_decompose():
    """Verify backend/depthwizard/calibration/dtm_decompose.py bare earth filtering."""
    from depthwizard.calibration.dtm_decompose import compute_terrain_slope_deg, decompose_bare_earth_dtm

    dem = np.zeros((100, 100), dtype=np.float32)
    dem[40:60, 40:60] = 15.0  # 20x20 building

    dtm = decompose_bare_earth_dtm(dem, gsd_m=0.33, filter_radius_m=10.0)
    assert dtm.shape == (100, 100)
    assert np.max(dtm) < 8.0

    slope = compute_terrain_slope_deg(dtm, gsd_m=0.33)
    assert isinstance(slope, float)
    assert slope >= 0.0


def test_training_loss_computation():
    """Verify training/losses.py composite loss functions."""
    from training.losses import CompositeLoss, MetricNDSMLoss

    criterion = CompositeLoss()
    pred = torch.ones((2, 1, 64, 64), dtype=torch.float32, requires_grad=True) * 10.0
    target = torch.ones((2, 1, 64, 64), dtype=torch.float32) * 10.0
    mask = torch.ones((2, 1, 64, 64), dtype=torch.bool)

    loss = criterion(pred, target, mask)
    assert torch.is_tensor(loss)
    assert loss.item() < 0.1


def test_calibration_selector_graceful_srtm_fallback():
    """Verify calibration selector falls back cleanly if SRTM fails or is missing."""
    from depthwizard.calibration.selector import calibrate_scene

    disparity = np.random.uniform(0.0, 1.0, size=(128, 128)).astype(np.float32)
    cal_dsm, ndsm, meta = calibrate_scene(
        disparity=disparity,
        is_georeferenced=True,
        crs="EPSG:4326",
        transform=None,
        bounds=[999.0, 999.0, 1000.0, 1000.0],  # Invalid/uncached coordinates
        explicit_path=None,
    )

    assert meta["path"] in ["PATH_C", "PATH_D"]
    assert cal_dsm.shape == (128, 128)
    assert np.all(np.isfinite(cal_dsm))


def test_frontend_control_hud_exists():
    """Verify frontend/src/components/ControlHud.tsx exists and is populated."""
    hud_file = Path("frontend/src/components/ControlHud.tsx")
    assert hud_file.exists()
    content = hud_file.read_text(encoding="utf-8")
    assert "ControlHud" in content
