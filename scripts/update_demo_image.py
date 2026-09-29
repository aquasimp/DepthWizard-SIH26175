"""Update all default and demo assets with the new user-uploaded aerial image."""

import json
import shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin

from depthwizard.api.routes_terrain import extract_mesh_dict
from depthwizard.jobs.manager import JobManager

SRC_IMG = Path(r"C:\Users\anura\.gemini\antigravity-ide\brain\a177de79-e8a7-4c71-bb60-d4252e8a27f3\.user_uploaded\media_1790662753038.jpg")
JOB_ID = "job_1790662888_5ffbdc8e"
ROOT = Path(__file__).resolve().parent.parent
JOB_DIR = ROOT / "jobs" / JOB_ID

def main():
    print(f"Loading source image from {SRC_IMG}...")
    pil_img = Image.open(SRC_IMG).convert("RGB")
    width, height = pil_img.size
    print(f"Image dimensions: {width}x{height}")

    # 1. Update PNG assets
    png_targets = [
        ROOT / "frontend" / "src" / "assets" / "sample_gamus_optical.png",
        ROOT / "frontend" / "public" / "sample_gamus_optical.png",
        ROOT / "frontend" / "public" / "active_texture.png",
        ROOT / "frontend" / "public" / "samples" / "sample_plain.png",
    ]
    for target in png_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        pil_img.save(target, format="PNG", optimize=True)
        print(f"Updated PNG: {target}")

    # 2. Update JPG assets
    jpg_targets = [
        ROOT / "frontend" / "public" / "samples" / "benchmark_optical.jpg",
        ROOT / "frontend" / "public" / "texture.jpg",
    ]
    for target in jpg_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        pil_img.save(target, format="JPEG", quality=95)
        print(f"Updated JPG: {target}")

    # 3. Create authentic GeoTIFF for benchmark_optical.tif
    rgb_np = np.array(pil_img)  # (H, W, 3)
    gsd_m = 0.33
    # Origin centered in UTM Zone 43N
    transform = from_origin(323000.0, 3160000.0, gsd_m, gsd_m)
    crs = rasterio.crs.CRS.from_epsg(32643)

    tif_targets = [
        ROOT / "frontend" / "public" / "samples" / "benchmark_optical.tif",
        ROOT / "frontend" / "public" / "samples" / "sample_georeferenced.tif",
        ROOT / "frontend" / "public" / "samples" / "sample_geographic.tif",
    ]
    for tif_path in tif_targets:
        with rasterio.open(
            tif_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=3,
            dtype=rasterio.uint8,
            crs=crs,
            transform=transform,
            compress="deflate",
        ) as dst:
            for b in range(3):
                dst.write(rgb_np[:, :, b], b + 1)
        print(f"Updated GeoTIFF: {tif_path}")

    # 4. Copy 16-bit Heightmap and generate DSM visualization
    heightmap_16bit_src = JOB_DIR / "heightmap_16bit.png"
    if heightmap_16bit_src.exists():
        shutil.copy2(heightmap_16bit_src, ROOT / "frontend" / "public" / "heightmap_16bit.png")
        print("Copied heightmap_16bit.png to frontend/public/")

        # Generate vibrant colormapped DSM visualization
        h_png = cv2.imread(str(heightmap_16bit_src), cv2.IMREAD_UNCHANGED)
        h_norm = ((h_png.astype(np.float32) / 65535.0) * 255.0).astype(np.uint8)
        dsm_color = cv2.applyColorMap(h_norm, cv2.COLORMAP_TURBO)
        dsm_vis_path = ROOT / "frontend" / "public" / "dsm_vis.png"
        cv2.imwrite(str(dsm_vis_path), dsm_color)
        print(f"Generated DSM visualization: {dsm_vis_path}")

    # 5. Copy reference DSM / LiDAR GT
    rdsm_src = JOB_DIR / "rdsm.tif"
    if rdsm_src.exists():
        shutil.copy2(rdsm_src, ROOT / "frontend" / "public" / "samples" / "benchmark_lidar_gt.tif")
        shutil.copy2(rdsm_src, ROOT / "frontend" / "public" / "samples" / "sample_reference_dsm.tif")
        print("Updated benchmark_lidar_gt.tif and sample_reference_dsm.tif")

    # 6. Generate authentic 128x128 terrain mesh json
    mgr = JobManager()
    mesh_dict = extract_mesh_dict(JOB_DIR, JOB_ID, resolution=128)
    mesh_dict["texture_url"] = "/samples/benchmark_optical.jpg"
    mesh_dict["dsm_vis_url"] = "/dsm_vis.png"

    mesh_targets = [
        ROOT / "frontend" / "src" / "data" / "default_terrain_mesh.json",
        ROOT / "frontend" / "public" / "data" / "default_terrain_mesh.json",
    ]
    for target in mesh_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(mesh_dict, f)
        print(f"Updated mesh JSON: {target} (min: {mesh_dict['min_height']:.1f}m, max: {mesh_dict['max_height']:.1f}m, aspect: {mesh_dict['aspect_ratio']:.3f})")

    # 7. Create a 'demo' alias in jobs/ so requests to /api/jobs/demo serve this new data
    demo_job_dir = ROOT / "jobs" / "demo"
    demo_job_dir.mkdir(parents=True, exist_ok=True)
    for f in JOB_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, demo_job_dir / f.name)
    print(f"Updated jobs/demo alias from {JOB_ID}")

    print("\nAll demo assets successfully replaced with the new image!")

if __name__ == "__main__":
    main()
