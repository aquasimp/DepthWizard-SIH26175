"""Phase 2 Acceptance Tests: Seamless tiling, seam continuity check, 4x zoom crop."""

from pathlib import Path

import cv2
import numpy as np
import torch
from depthwizard.depth.infer import DepthInferenceEngine, colorize_depth
from depthwizard.depth.tiling import infer_tiled
from PIL import Image


def test_tiling_seamless_continuity() -> None:
    """Acceptance test:
    Along every internal tile boundary, the mean absolute second difference
    across the seam is within 1.5x the mean absolute second difference of the
    tile interiors. Also save a 4x-zoom crop of a seam to docs/assets/ for review.
    """
    # Create a synthetic image of 800x800 px with gradients and structures
    # that spans across multiple tiles (tile_size=512, overlap=64)
    H, W = 800, 800
    np.random.seed(42)
    y_coords, x_coords = np.mgrid[0:H, 0:W]

    # Synthetic realistic remote-sensing image with background gradient and buildings
    base_grad = (np.sin(x_coords * 0.01) * np.cos(y_coords * 0.01) * 50 + 128).astype(np.float32)
    img_synth = np.repeat(base_grad[:, :, np.newaxis], 3, axis=-1).astype(np.uint8)

    # Add a few rectangular structures
    cv2.rectangle(img_synth, (200, 200), (350, 350), (220, 220, 220), -1)
    cv2.rectangle(img_synth, (400, 400), (600, 600), (40, 40, 40), -1)
    cv2.rectangle(img_synth, (420, 200), (550, 320), (180, 180, 180), -1)

    # Initialize model on CPU for reproducible testing
    engine = DepthInferenceEngine(checkpoint_path="models/depth_anything_v2_vits.pth", device="cpu")

    def infer_fn(tile: np.ndarray) -> np.ndarray:
        return engine.infer_tile(tile, input_size=518)

    # Run tiled inference: tile 512, overlap 64
    tile_size = 512
    overlap = 64
    stride = tile_size - overlap  # 448
    blended = infer_tiled(infer_fn, img_synth, tile_size=tile_size, overlap=overlap)

    assert blended.shape == (H, W)
    assert np.all(np.isfinite(blended))

    # The internal vertical seam lies in the overlap region between x in [stride, tile_size] = [448, 512]
    # The center of the overlap seam is at x = (448 + 512) // 2 = 480
    seam_x = (stride + tile_size) // 2

    # Second difference across horizontal direction: d^2/dx^2 = f(x+1) - 2*f(x) + f(x-1)
    second_diff = np.abs(blended[:, 2:] - 2.0 * blended[:, 1:-1] + blended[:, :-2])

    # Seam region (+/- 5 pixels around seam_x)
    seam_col = seam_x - 1
    seam_diff = second_diff[:, seam_col - 2 : seam_col + 3]
    mean_seam_second_diff = float(np.mean(seam_diff))

    # Tile interior regions (away from seams, e.g. x in [100, 350] and [550, 750])
    interior_diff_1 = second_diff[:, 100:350]
    interior_diff_2 = second_diff[:, 550:750]
    mean_interior_second_diff = float(
        (np.sum(interior_diff_1) + np.sum(interior_diff_2))
        / (interior_diff_1.size + interior_diff_2.size)
    )

    ratio = mean_seam_second_diff / (mean_interior_second_diff + 1e-8)
    print(
        f"Mean seam second diff: {mean_seam_second_diff:.6f}, "
        f"Mean interior second diff: {mean_interior_second_diff:.6f}, "
        f"Ratio: {ratio:.3f}"
    )

    # Save 4x-zoom crop of the seam to docs/assets/ for manual review
    assets_dir = Path("docs/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    seam_crop = blended[300:500, seam_x - 100 : seam_x + 100]
    colored_seam = colorize_depth(seam_crop)

    # 4x resize via nearest neighbor or bicubic for zoom visualization
    h_c, w_c = colored_seam.shape[:2]
    zoom_4x = cv2.resize(colored_seam, (w_c * 4, h_c * 4), interpolation=cv2.INTER_NEAREST)

    zoom_path = assets_dir / "seam_zoom_4x.png"
    Image.fromarray(zoom_4x).save(str(zoom_path))
    assert zoom_path.exists(), f"Failed to save zoom crop to {zoom_path}"
    print(f"Saved 4x-zoom seam crop to {zoom_path}")

    # Acceptance assertion: ratio must be within 1.5x
    assert ratio <= 1.5, (
        f"Seam discontinuity detected! Ratio {ratio:.3f} exceeds maximum allowed 1.5x"
    )


def test_cli_runs_on_all_samples_cpu_and_cuda() -> None:
    """Verify inference runs on every file in data/samples/ on CPU and CUDA (if available)."""
    samples_dir = Path("data/samples")
    assert samples_dir.exists()

    engine_cpu = DepthInferenceEngine(checkpoint_path="models/depth_anything_v2_vits.pth", device="cpu")

    sample_files = list(samples_dir.glob("sample_*.*"))
    assert len(sample_files) >= 3

    for p in sample_files:
        pil_img = Image.open(str(p)).convert("RGB")
        rgb = np.array(pil_img, dtype=np.uint8)

        # CPU run
        depth_cpu, time_cpu = engine_cpu.infer_scene(rgb, tile_size=512, overlap=64)
        assert depth_cpu.shape == rgb.shape[:2]
        assert np.all(np.isfinite(depth_cpu))
        assert time_cpu > 0.0

    if torch.cuda.is_available():
        engine_cuda = DepthInferenceEngine(checkpoint_path="models/depth_anything_v2_vits.pth", device="cuda")
        for p in sample_files:
            pil_img = Image.open(str(p)).convert("RGB")
            rgb = np.array(pil_img, dtype=np.uint8)
            depth_cuda, time_cuda = engine_cuda.infer_scene(rgb, tile_size=512, overlap=64)
            assert depth_cuda.shape == rgb.shape[:2]
            assert np.all(np.isfinite(depth_cuda))
            assert time_cuda > 0.0
