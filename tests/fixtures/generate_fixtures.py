"""Generate synthetic GeoTIFF and image fixtures for DepthWizard tests."""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.transform import Affine, from_origin


def generate_all_fixtures(fixtures_dir: Path) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    h, w = 100, 100
    # Gradient test image (H, W, 3)
    y, x = np.mgrid[0:h, 0:w]
    r = (x * 255 // w).astype(np.uint8)
    g = (y * 255 // h).astype(np.uint8)
    b = ((x + y) * 255 // (w + h)).astype(np.uint8)
    rgb = np.stack([r, g, b], axis=0)  # (3, H, W) for rasterio

    # 1. projected_metres.tif (EPSG:32618, 1.0 m GSD)
    proj_transform = from_origin(580000.0, 4500000.0, 1.0, 1.0)
    with rasterio.open(
        fixtures_dir / "projected_metres.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype="uint8",
        crs=CRS.from_epsg(32618),
        transform=proj_transform,
    ) as dst:
        dst.write(rgb)

    # 2. geographic_degrees.tif (EPSG:4326, 0.00001 deg GSD, lat ~28.6139)
    geo_transform = from_origin(77.2090, 28.6139, 0.00001, 0.00001)
    with rasterio.open(
        fixtures_dir / "geographic_degrees.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype="uint8",
        crs=CRS.from_epsg(4326),
        transform=geo_transform,
    ) as dst:
        dst.write(rgb)

    # 3. no_crs.tif (no CRS, identity transform)
    with rasterio.open(
        fixtures_dir / "no_crs.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype="uint8",
        crs=None,
        transform=Affine.identity(),
    ) as dst:
        dst.write(rgb)

    # 4. rotated.tif (transform with b != 0 and d != 0)
    # 30 degree rotation
    rot_transform = Affine(0.866, -0.5, 580000.0, 0.5, 0.866, 4500000.0)
    with rasterio.open(
        fixtures_dir / "rotated.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype="uint8",
        crs=CRS.from_epsg(32618),
        transform=rot_transform,
    ) as dst:
        dst.write(rgb)

    # 5. uint16.tif (16-bit values up to 60000)
    rgb16 = rgb.astype(np.uint16) * 235  # values up to ~59925
    with rasterio.open(
        fixtures_dir / "uint16.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype="uint16",
        crs=CRS.from_epsg(32618),
        transform=from_origin(580000.0, 4500000.0, 0.5, 0.5),
    ) as dst:
        dst.write(rgb16)

    # 6. single_band.tif (grayscale uint8)
    with rasterio.open(
        fixtures_dir / "single_band.tif",
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="uint8",
        crs=CRS.from_epsg(32618),
        transform=from_origin(580000.0, 4500000.0, 0.5, 0.5),
    ) as dst:
        dst.write(r[np.newaxis, :, :])

    # 7. corrupt.tif (corrupt binary file)
    corrupt_path = fixtures_dir / "corrupt.tif"
    corrupt_path.write_bytes(
        b"NOT_A_VALID_TIFF_FILE_CORRUPT_HEADER_AND_BODY\x00\xff\xfe\x00\x01\x02"
    )

    # 8. plain.png (standard PNG without geospatial metadata)
    img_pil = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    img_pil.save(fixtures_dir / "plain.png")

    # 9. plain.jpg (standard JPEG without geospatial metadata)
    img_pil.save(fixtures_dir / "plain.jpg", quality=95)


if __name__ == "__main__":
    fixtures_dir = Path(__file__).resolve().parent
    generate_all_fixtures(fixtures_dir)
    print("All fixtures generated successfully.")
