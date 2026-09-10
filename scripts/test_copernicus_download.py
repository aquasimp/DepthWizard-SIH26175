import urllib.request
from pathlib import Path

target_dir = Path("X:/DatasetsSIH 26175/02_CALIBRATION_AND_DATUM_DEM/COPERNICUS_GLO30/sample_tiles")
target_dir.mkdir(parents=True, exist_ok=True)

# Copernicus DEM GLO-30 tile over Washington D.C. (N38 W078)
url = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N38_00_W078_00_DEM/Copernicus_DSM_COG_10_N38_00_W078_00_DEM.tif"
print(f"Testing Copernicus DEM URL: {url}")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "DepthWizard-Research/1.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        size = int(resp.headers.get("Content-Length", 0))
        print(f"Copernicus tile available! Size: {size} bytes ({size / (1024*1024):.2f} MB)")
except Exception as e:
    print(f"Failed to access Copernicus tile: {e}")
