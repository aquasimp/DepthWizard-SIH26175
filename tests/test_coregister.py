"""Unit tests for phase cross-correlation sub-pixel coregistration."""

import numpy as np
import pytest
import scipy.ndimage as ndi

from depthwizard.eval.coregister import coregister_grids


def test_coregister_recovers_known_shift():
    """Verify sub-pixel translation recovery on synthetic smooth terrain."""
    np.random.seed(1234)
    # Generate smooth continuous terrain surface
    base = ndi.gaussian_filter(np.random.randn(128, 128) * 10.0 + 100.0, sigma=4.0)

    # Shift reference by +2.0 row, -3.0 col
    true_dy, true_dx = 2.0, -3.0
    ref_shifted = ndi.shift(base, (true_dy, true_dx), order=3, mode="nearest")

    pred_grid = base.astype(np.float32)
    ref_grid = ref_shifted.astype(np.float32)

    initial_rmse = float(np.sqrt(np.mean((pred_grid[10:-10, 10:-10] - ref_grid[10:-10, 10:-10]) ** 2)))

    aligned_pred, aligned_ref, info = coregister_grids(pred_grid, ref_grid, max_shift=10.0)

    assert info["shift_applied"] is True
    # The shift applied to ref to align with pred should be approximately (-true_dy, -true_dx)
    assert pytest.approx(info["shift_y"], abs=0.25) == -true_dy
    assert pytest.approx(info["shift_x"], abs=0.25) == -true_dx

    # Post-alignment RMSE in central interior should drop dramatically
    final_rmse = float(np.sqrt(np.mean((aligned_pred[15:-15, 15:-15] - aligned_ref[15:-15, 15:-15]) ** 2)))
    assert final_rmse < initial_rmse * 0.5


def test_coregister_no_shift():
    """Verify that identical rasters are not resampled."""
    grid = np.linspace(10.0, 50.0, 10000, dtype=np.float32).reshape(100, 100)

    pred, aligned_ref, info = coregister_grids(grid, grid.copy())

    assert info["shift_applied"] is False
    assert info["shift_magnitude"] < 0.05
    np.testing.assert_array_equal(grid, aligned_ref)


def test_coregister_excessive_shift_rejected():
    """Verify that shifts beyond max_shift are rejected with a warning."""
    np.random.seed(42)
    base = ndi.gaussian_filter(np.random.randn(128, 128) * 10.0, sigma=4.0)
    # Huge shift of 20 pixels (exceeds max_shift=15)
    shifted = ndi.shift(base, (20.0, 0.0), order=1, mode="nearest")

    _, aligned_ref, info = coregister_grids(base, shifted, max_shift=10.0)

    assert info["shift_applied"] is False
    assert info["warning"] is not None
    assert "exceeds max threshold" in info["warning"]


def test_coregister_insufficient_data():
    """Verify safe fallback when rasters have insufficient valid pixels."""
    pred = np.full((50, 50), -9999.0, dtype=np.float32)
    ref = np.full((50, 50), -9999.0, dtype=np.float32)

    _, _, info = coregister_grids(pred, ref)

    assert info["shift_applied"] is False
    assert "Insufficient" in info["warning"]
