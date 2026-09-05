"""GDALinfo compatibility CLI for DepthWizard environment.

Uses rasterio/GDAL Python bindings to print dataset metadata, CRS, and bounds
in standard gdalinfo formatting.
"""

import sys
from pathlib import Path

import rasterio


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: gdalinfo <dataset_path>")
        return 1

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"ERROR 4: `{path}` does not exist in the file system.")
        return 1

    try:
        with rasterio.open(path) as src:
            print(f"Driver: {src.driver}/{src.driver}")
            print(f"Files: {path}")
            print(f"Size is {src.width}, {src.height}")
            if src.crs:
                print("Coordinate System is:")
                print(src.crs.to_wkt())
            else:
                print("Coordinate System is: (none)")

            if src.transform:
                gt = src.transform
                print(f"Origin = ({gt.c:.6f},{gt.f:.6f})")
                print(f"Pixel Size = ({gt.a:.6f},{gt.e:.6f})")

            bounds = src.bounds
            print("Corner Coordinates:")
            print(f"Upper Left  ( {bounds.left:12.3f}, {bounds.top:12.3f})")
            print(f"Lower Left  ( {bounds.left:12.3f}, {bounds.bottom:12.3f})")
            print(f"Upper Right ( {bounds.right:12.3f}, {bounds.top:12.3f})")
            print(f"Lower Right ( {bounds.right:12.3f}, {bounds.bottom:12.3f})")
            print(f"Center      ( {(bounds.left+bounds.right)/2:12.3f}, {(bounds.top+bounds.bottom)/2:12.3f})")

            for i in range(1, src.count + 1):
                desc = src.descriptions[i - 1] or ""
                dt = src.dtypes[i - 1]
                nd = src.nodata
                block = src.block_shapes[i - 1]
                print(f"Band {i} Block={block[1]}x{block[0]} Type={dt}, ColorInterp=Gray")
                if desc:
                    print(f"  Description = {desc}")
                if nd is not None:
                    print(f"  NoData Value={nd}")
        return 0
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
