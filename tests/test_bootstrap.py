"""Phase 0 Bootstrap verification tests."""

import os
from pathlib import Path


def test_core_imports() -> None:
    """Verify that all core geospatial, ML, and meshing libraries are importable."""
    import cv2
    import pyproj
    import rasterio
    import torch
    import trimesh

    assert rasterio is not None
    assert torch is not None
    assert trimesh is not None
    assert pyproj is not None
    assert cv2 is not None


def test_weights_file_exists_and_size() -> None:
    """Verify Depth Anything V2 Small weights are present with exact expected size."""
    weights_path = Path("models/depth_anything_v2_vits.pth")
    assert weights_path.exists(), f"Weights file missing at {weights_path}"
    expected_size = 99218434
    actual_size = os.path.getsize(weights_path)
    assert actual_size == expected_size, (
        f"Weights size mismatch: expected {expected_size}, got {actual_size}"
    )
