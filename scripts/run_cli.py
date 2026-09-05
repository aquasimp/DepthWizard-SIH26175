"""DepthWizard CLI: Single-View Height Estimation on Local Imagery."""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

# Ensure backend package is importable
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from depthwizard.depth.infer import DepthInferenceEngine, colorize_depth  # noqa: E402


def load_input_rgb(path: Path) -> np.ndarray:
    """Load image as uint8 RGB (H, W, 3) from GeoTIFF, TIFF, PNG, or JPG."""
    if path.suffix.lower() in [".tif", ".tiff"]:
        try:
            with rasterio.open(str(path)) as src:
                count = src.count
                if count >= 3:
                    r = src.read(1)
                    g = src.read(2)
                    b = src.read(3)
                    rgb = np.stack([r, g, b], axis=-1)
                else:
                    gray = src.read(1)
                    rgb = np.stack([gray, gray, gray], axis=-1)

                if rgb.dtype != np.uint8:
                    if rgb.max() > 255:
                        rgb = (rgb / (rgb.max() / 255.0)).astype(np.uint8)
                    else:
                        rgb = rgb.astype(np.uint8)
                return rgb
        except Exception:
            pass

    # Fallback to PIL
    pil_img = Image.open(str(path)).convert("RGB")
    return np.array(pil_img, dtype=np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description="DepthWizard CLI: Single-View Elevation Estimation")
    parser.add_argument("--input", "-i", required=True, help="Path to input image (PNG, JPG, GeoTIFF)")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Output directory")
    parser.add_argument("--mode", choices=["relative", "metric"], default="metric", help="Inference mode")
    parser.add_argument("--device", default="auto", help="Compute device (auto, cuda, cpu)")
    parser.add_argument("--checkpoint", default="models/depth_anything_v2_vits.pth", help="Model checkpoint path")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist at {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading input: {input_path}...")
    rgb = load_input_rgb(input_path)
    h, w = rgb.shape[:2]
    print(f"Input dimensions: {w}x{h} px, 3 channels")

    engine = DepthInferenceEngine(checkpoint_path=args.checkpoint, device=args.device)
    print(f"Executing inference on device: {engine.device} (mode: {args.mode})...")

    start_time = time.perf_counter()
    depth, wall_time = engine.infer_scene(rgb, tile_size=512, overlap=64)
    total_time = time.perf_counter() - start_time

    print(f"Inference complete in {wall_time:.3f} s (total wall time: {total_time:.3f} s)")
    print(f"Depth min: {float(depth.min()):.3f}, max: {float(depth.max()):.3f}, mean: {float(depth.mean()):.3f}")

    stem = input_path.stem
    npy_path = out_dir / f"{stem}_depth.npy"
    np.save(str(npy_path), depth)
    print(f"Saved raw depth array: {npy_path}")

    color_depth = colorize_depth(depth)
    png_path = out_dir / f"{stem}_depth_color.png"
    Image.fromarray(color_depth).save(str(png_path))
    print(f"Saved colorized depth image: {png_path}")


if __name__ == "__main__":
    main()
