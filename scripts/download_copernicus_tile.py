import urllib.request
import time
from pathlib import Path

target_dir = Path("X:/DatasetsSIH 26175/02_CALIBRATION_AND_DATUM_DEM/COPERNICUS_GLO30/sample_tiles")
target_dir.mkdir(parents=True, exist_ok=True)

url = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N38_00_W078_00_DEM/Copernicus_DSM_COG_10_N38_00_W078_00_DEM.tif"
dest = target_dir / "Copernicus_DSM_COG_10_N38_00_W078_00_DEM.tif"

if dest.exists() and dest.stat().st_size > 1000000:
    print(f"{dest.name} already downloaded ({dest.stat().st_size} bytes).")
else:
    print(f"Downloading real Copernicus GLO-30 tile (45.58 MB) from AWS...")
    t0 = time.time()
    urllib.request.urlretrieve(url, dest)
    t1 = time.time()
    print(f"Download complete: {dest.stat().st_size} bytes in {t1-t0:.2f}s ({dest.stat().st_size/(1024*1024)/(t1-t0):.2f} MB/s)")
