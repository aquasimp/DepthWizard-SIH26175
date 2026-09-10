import urllib.request
import time
from pathlib import Path

target_dir = Path("X:/DatasetsSIH 26175/05_RECOMMENDED_AND_AUXILIARY_RESOURCES/USGS_3DEP_LiDAR_DEM/sample_1m_dem_tiles")
target_dir.mkdir(parents=True, exist_ok=True)

# Sample 1m DEM GeoTIFF covering an urban Jacksonville FL section (matching US3D study area)
url = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/FL_Peninsular_2018/TIFF/USGS_1M_17_x43y336_FL_Peninsular_2018.tif"
dest_file = target_dir / "USGS_1M_17_x43y336_FL_Peninsular_2018.tif"

print(f"Checking USGS 1m DEM tile: {url}")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "DepthWizard-Research/1.1"})
    with urllib.request.urlopen(req, timeout=10) as response:
        size = int(response.headers.get("Content-Length", 0))
        print(f"File size on AWS: {size} bytes ({size / (1024*1024):.2f} MB)")
        
        # If less than 20MB, download directly as a working demonstration sample
        if size > 0 and size < 25 * 1024 * 1024:
            print(f"Downloading sample tile to {dest_file}...")
            t0 = time.time()
            urllib.request.urlretrieve(url, dest_file)
            print(f"Downloaded successfully in {time.time()-t0:.2f}s!")
        else:
            print(f"Tile is {size/(1024*1024):.2f} MB. Preserving URL and metadata.")
except Exception as e:
    print(f"Error accessing USGS AWS tile: {e}")
