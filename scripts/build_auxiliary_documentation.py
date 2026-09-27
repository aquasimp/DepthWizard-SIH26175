"""
Generate all structured directories, access guides, target folders,
and acquisition documentation for auxiliary and recommended datasets
in X:\\DatasetsSIH 26175.
"""

from pathlib import Path
import os

BASE_DIR = Path("X:/DatasetsSIH 26175")

# 1. IEEE GRSS DFC 2019 (US3D)
dfc2019_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES" / "IEEE_GRSS_DFC2019_US3D"
dfc2019_dir.mkdir(parents=True, exist_ok=True)
(dfc2019_dir / "raw_downloads").mkdir(exist_ok=True)
(dfc2019_dir / "track1_single_view_semantic_3d").mkdir(exist_ok=True)
(dfc2019_dir / "track2_multi_view_semantic_3d").mkdir(exist_ok=True)

dfc2019_guide = """# IEEE GRSS Data Fusion Contest 2019 (US3D Dataset)
**Track 1: Single-View Semantic 3D (WorldView-3 to Metric nDSM)**

## 1. Overview & Relevance to DepthWizard
- **Relevance**: Direct 1-to-1 match for DepthWizard Problem Statement 26175. Track 1 specifically tested monocular single-view satellite optical RGB -> dense metric height (LiDAR nDSM in meters) and semantic segmentation.
- **Coverage Areas**: Jacksonville, Florida and Omaha, Nebraska, USA.
- **Sensors**: 
  - Optical: WorldView-3 commercial satellite (0.3m ground sample distance pan-sharpened RGB).
  - Ground Truth Elevation: Airborne LiDAR point clouds rasterized into 0.5m GSD bare-earth DEM and normalized Digital Surface Model (nDSM, meters above ground).
  - Semantic Labels: High-resolution ground truth masks for buildings, elevated roads, trees, water, and ground.

## 2. Official Metadata & Citation
- **Authoring Organization**: IEEE Geoscience and Remote Sensing Society (GRSS) Image Analysis and Data Fusion Technical Committee (IADF TC) & Johns Hopkins University Applied Physics Laboratory (JHU/APL).
- **Official DOI**: [10.21227/z5rc-qb87](https://dx.doi.org/10.21227/z5rc-qb87)
- **Official Landing Page**: [https://ieee-dataport.org/open-access/data-fusion-contest-2019-dfc2019](https://ieee-dataport.org/open-access/data-fusion-contest-2019-dfc2019)
- **Open Access License**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).

## 3. Access & Download Requirements
- **Authentication**: IEEE DataPort account required (free registration using any standard email or Google/ORCID SSO).
- **Payment**: 100% Free under Open Access.
- **Automated Download Restriction**: IEEE DataPort uses session cookies and Cloudflare protection; direct anonymous curl/wget requests return HTTP 403 Forbidden.

## 4. How to Download and Place Files
1. Navigate to: [https://ieee-dataport.org/open-access/data-fusion-contest-2019-dfc2019](https://ieee-dataport.org/open-access/data-fusion-contest-2019-dfc2019)
2. Log in with your IEEE credentials.
3. In the **Data Files** section, locate the Track 1 archives:
   - `Track1-MSI.tar.gz` (Pan-sharpened multispectral/RGB tiles)
   - `Track1-Truth.tar.gz` (Ground truth nDSM elevation GeoTIFFs + semantic masks)
4. Download the archives and place them into:
   `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\IEEE_GRSS_DFC2019_US3D\\raw_downloads\\`
5. Extract the files into:
   `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\IEEE_GRSS_DFC2019_US3D\\track1_single_view_semantic_3d\\`

## 5. Dataset Structure Once Extracted
```
track1_single_view_semantic_3d/
  ├── RGB/              # WorldView-3 pan-sharpened 3-band / 8-band imagery (.tif)
  ├── nDSM/             # Normalized Digital Surface Model heights in meters (.tif)
  ├── CLS/              # Integer land-cover classification labels (.tif)
  └── METADATA/         # RPC sensor models and acquisition timestamps
```

## 6. DepthWizard Benchmark Evaluation Protocol
Once extracted, run the DepthWizard batch evaluation harness:
```bash
python scripts/evaluate_us3d_benchmark.py \\
    --image-dir "X:/DatasetsSIH 26175/05_RECOMMENDED_AND_AUXILIARY_RESOURCES/IEEE_GRSS_DFC2019_US3D/track1_single_view_semantic_3d/RGB" \\
    --ndsm-dir "X:/DatasetsSIH 26175/05_RECOMMENDED_AND_AUXILIARY_RESOURCES/IEEE_GRSS_DFC2019_US3D/track1_single_view_semantic_3d/nDSM" \\
    --model "X:/DatasetsSIH 26175/03_PRETRAINED_MODELS_AND_WEIGHTS/DepthWizard_FineTuned_v1.1.0/dav3s_gamus_ft_v1.pth"
```
"""
(dfc2019_dir / "ACCESS_AND_DOWNLOAD_GUIDE.md").write_text(dfc2019_guide, encoding="utf-8")


# 2. IEEE GRSS DFC 2023 (Track 2)
dfc2023_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES" / "IEEE_GRSS_DFC2023_Track2"
dfc2023_dir.mkdir(parents=True, exist_ok=True)
(dfc2023_dir / "raw_downloads").mkdir(exist_ok=True)
(dfc2023_dir / "building_height_estimation_17_cities").mkdir(exist_ok=True)

dfc2023_guide = """# IEEE GRSS Data Fusion Contest 2023 (Track 2)
**Large-Scale Building Extraction and Height Estimation from Satellite Imagery**

## 1. Overview & Relevance to DepthWizard
- **Relevance**: Evaluates the generalization of height estimation across 17 diverse global cities across 6 continents. Tests urban morphology variations (dense high-rise, suburban residential, industrial complexes, informal settlements).
- **Coverage**: 17 cities globally (including Berlin, Mumbai, São Paulo, Tokyo, Nairobi, etc.).
- **Sensors**: SuperView-1 and Gaofen-2 high-resolution satellite imagery (0.5m - 0.8m GSD) with airborne LiDAR and stereo-derived ground truth building footprints and rooftop heights.

## 2. Official Metadata & Citation
- **Authoring Organization**: IEEE GRSS IADF TC & Aerospace Information Research Institute, Chinese Academy of Sciences.
- **Official DOI**: [10.21227/xzk6-k131](https://dx.doi.org/10.21227/xzk6-k131)
- **Official Landing Page**: [https://ieee-dataport.org/competitions/data-fusion-contest-2023-dfc2023](https://ieee-dataport.org/competitions/data-fusion-contest-2023-dfc2023)
- **Competition Repository**: [https://github.com/ChenHongruixuan/DFC2023-Track2-Baseline](https://github.com/ChenHongruixuan/DFC2023-Track2-Baseline)

## 3. Access & Download Requirements
- **Authentication**: IEEE DataPort login required.
- **Participation Terms**: Accept DFC 2023 research terms of use on IEEE DataPort.
- **Direct Link**: Gated behind session login.

## 4. How to Download and Place Files
1. Sign in to IEEE DataPort: [https://ieee-dataport.org/competitions/data-fusion-contest-2023-dfc2023](https://ieee-dataport.org/competitions/data-fusion-contest-2023-dfc2023)
2. Download Track 2 zip archives:
   - `DFC2023_Track2_train.zip`
   - `DFC2023_Track2_val.zip`
3. Save archives to:
   `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\IEEE_GRSS_DFC2023_Track2\\raw_downloads\\`
4. Unpack to:
   `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\IEEE_GRSS_DFC2023_Track2\\building_height_estimation_17_cities\\`
"""
(dfc2023_dir / "ACCESS_AND_DOWNLOAD_GUIDE.md").write_text(dfc2023_guide, encoding="utf-8")


# 3. ISPRS Potsdam & Vaihingen
isprs_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES" / "ISPRS_Potsdam_Vaihingen"
isprs_dir.mkdir(parents=True, exist_ok=True)
(isprs_dir / "potsdam").mkdir(exist_ok=True)
(isprs_dir / "vaihingen").mkdir(exist_ok=True)

isprs_guide = """# ISPRS 2D/3D Semantic Labeling Benchmark (Potsdam & Vaihingen)

## 1. Overview & Relevance to DepthWizard
- **Relevance**: Standard European airborne photogrammetry benchmark with sub-decimeter ground resolution and co-registered dense LiDAR DSM / nDSM. Perfect for testing DepthWizard on ultra-high-resolution aerial drone/aircraft imagery.
- **Datasets**:
  1. **Potsdam**: 0.05m GSD, 38 tiles of 6000x6000 px. Contains True Orthophotos (TOP RGB, IRRG, RGBIR), dense DSM, normalized DSM (nDSM), and ground truth labels.
  2. **Vaihingen**: 0.09m GSD, 33 patches of varying size (avg 2500x2000 px). Contains TOP (IRRG) + dense LiDAR DSM + nDSM.

## 2. Official Metadata & Citation
- **Authoring Organization**: International Society for Photogrammetry and Remote Sensing (ISPRS) Commission II / WG II/4.
- **Official Portal**: [https://www.isprs.org/education/benchmarks/UrbanSemLab/default.aspx](https://www.isprs.org/education/benchmarks/UrbanSemLab/default.aspx)
- **Potsdam Details**: [https://www.isprs.org/education/benchmarks/UrbanSemLab/2d-sem-label-potsdam.aspx](https://www.isprs.org/education/benchmarks/UrbanSemLab/2d-sem-label-potsdam.aspx)
- **Vaihingen Details**: [https://www.isprs.org/education/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx](https://www.isprs.org/education/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx)

## 3. Access Requirements
- Free registration form on the ISPRS website.
- After submitting your academic/developer affiliation, direct HTTP download credentials (username & password) are sent via automated email.

## 4. How to Download and Place Files
1. Visit the registration page: [https://www.isprs.org/education/benchmarks/UrbanSemLab/default.aspx](https://www.isprs.org/education/benchmarks/UrbanSemLab/default.aspx)
2. Submit your registration details to receive FTP/HTTP credentials.
3. Download:
   - `2_Ortho_RGB.zip` (Potsdam RGB orthophotos)
   - `1_DSM_normalisation.zip` (Potsdam nDSM normalized heights)
   - `ISPRS_semantic_labeling_Vaihingen.zip` (Vaihingen imagery + DSM/nDSM)
4. Place files in:
   - `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\ISPRS_Potsdam_Vaihingen\\potsdam\\`
   - `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\ISPRS_Potsdam_Vaihingen\\vaihingen\\`
"""
(isprs_dir / "ACCESS_AND_DOWNLOAD_GUIDE.md").write_text(isprs_guide, encoding="utf-8")


# 4. USGS 3DEP LiDAR & 1m DEMs
usgs_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES" / "USGS_3DEP_LiDAR_DEM"
usgs_dir.mkdir(parents=True, exist_ok=True)
(usgs_dir / "sample_1m_dem_tiles").mkdir(exist_ok=True)

usgs_guide = """# USGS 3D Elevation Program (3DEP) High-Resolution LiDAR & Bare-Earth DEMs

## 1. Overview & Relevance to DepthWizard
- **Relevance**: Gold standard for high-accuracy nationwide 3D topography and LiDAR ground truth in the United States. Used as the underlying ground truth source by GAMUS and US3D datasets.
- **Products**:
  - 1-meter seamless bare-earth DEMs (GeoTIFF, 32-bit floating point elevation).
  - 1/3-arc-second (~10m) seamless DEMs.
  - Cloud-Optimized Point Clouds (COPC / LAZ) from airborne LiDAR surveys.

## 2. Official Metadata & Access
- **Authoring Organization**: United States Geological Survey (USGS) National Geospatial Program.
- **Official Portal**: [https://www.usgs.gov/3d-elevation-program](https://www.usgs.gov/3d-elevation-program)
- **AWS Open Data Registry**: [https://registry.opendata.aws/usgs-lidar/](https://registry.opendata.aws/usgs-lidar/)
- **Direct S3 / HTTP Bucket**: `https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/Elevation/1m/`
- **License**: Public Domain (US Government Work, CC0). Free, no registration, no API key.

## 3. Direct Programmatic Download Script
A dedicated python script `download_usgs_sample.py` is provided in this directory to fetch sample 1m DEM tiles covering urban test areas:
```bash
python scripts/download_usgs_sample.py
```
Or directly via curl:
```bash
curl -O "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/FL_Peninsular_2018/TIFF/USGS_1M_17_x43y336_FL_Peninsular_2018.tif"
```
Place all downloaded GeoTIFFs in:
`X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\USGS_3DEP_LiDAR_DEM\\sample_1m_dem_tiles\\`
"""
(usgs_dir / "ACCESS_AND_DOWNLOAD_GUIDE.md").write_text(usgs_guide, encoding="utf-8")


# 5. ISRO CartoDEM (Bhuvan)
isro_dir = BASE_DIR / "05_RECOMMENDED_AND_AUXILIARY_RESOURCES" / "ISRO_CartoDEM_Bhuvan"
isro_dir.mkdir(parents=True, exist_ok=True)
(isro_dir / "indian_aoi_tiles").mkdir(exist_ok=True)

isro_guide = """# ISRO CartoDEM (Cartosat-1 30m Indian National DEM)
**Official Elevation Model for Indian Territory (Problem Statement 26175 Domain Context)**

## 1. Overview & Relevance to DepthWizard
- **Relevance**: CartoDEM is the official national digital elevation model produced by the Indian Space Research Organisation (ISRO) and National Remote Sensing Centre (NRSC) using stereo pairs from the Cartosat-1 satellite at 2.5m resolution, resampled to 30m grid spacing.
- **Importance for SIH 26175**: Problem statement 26175 originated from ISRO / Space Applications Centre (SAC). Validating DepthWizard against CartoDEM over Indian cities (Ahmedabad, Bengaluru, Delhi NCR, Hyderabad) demonstrates direct operational readiness for ISRO/SAC deployment.
- **Coverage**: Complete Indian landmass and surrounding offshore islands.

## 2. Official Metadata & Portal
- **Authoring Organization**: National Remote Sensing Centre (NRSC) / Indian Space Research Organisation (ISRO).
- **Official Portal**: [https://bhuvan-app3.nrsc.gov.in/data/download/index.php](https://bhuvan-app3.nrsc.gov.in/data/download/index.php)
- **Alternative Open Data**: Open data tiles available under the Indian National Geospatial Policy 2022.

## 3. Access & Download Requirements
- **Authentication**: Free registration on ISRO Bhuvan portal. Mobile number / email OTP verification required.
- **Terms**: Non-commercial scientific and research use.
- **Automated Download Restriction**: Bhuvan portal uses interactive map tile selection and session-bound tokens; automated scraping is strictly blocked by NRSC security firewalls.

## 4. How to Obtain CartoDEM Tiles
1. Navigate to Bhuvan Data Download: [https://bhuvan-app3.nrsc.gov.in/data/download/index.php](https://bhuvan-app3.nrsc.gov.in/data/download/index.php)
2. Under "Select Category", choose **Terrain / Elevation Data**.
3. Under "Select Product", select **CartoDEM - 30m (Version 3 R1)**.
4. Select your Area of Interest (AOI):
   - By bounding box or administrative district (e.g., Gujarat -> Ahmedabad; Karnataka -> Bengaluru Urban).
5. Click **Download** for the selected 1x1 degree GeoTIFF tiles (e.g., `cartodem_ahmedabad_30m.tif`).
6. Place the downloaded tiles into:
   `X:\\DatasetsSIH 26175\\05_RECOMMENDED_AND_AUXILIARY_RESOURCES\\ISRO_CartoDEM_Bhuvan\\indian_aoi_tiles\\`

## 5. Integrating with DepthWizard Path A Calibration
CartoDEM can be passed directly to DepthWizard CLI as the reference datum:
```bash
python run_pipeline.py \\
    --input "data/samples/optical_samples/sample_georeferenced.tif" \\
    --datum-dem "X:/DatasetsSIH 26175/05_RECOMMENDED_AND_AUXILIARY_RESOURCES/ISRO_CartoDEM_Bhuvan/indian_aoi_tiles/cartodem_ahmedabad_30m.tif" \\
    --calibration-mode datum_decompose
```
"""
(isro_dir / "ACCESS_AND_DOWNLOAD_GUIDE.md").write_text(isro_guide, encoding="utf-8")


# 6. Copernicus DEM (GLO-30)
cop_dir = BASE_DIR / "02_CALIBRATION_AND_DATUM_DEM" / "COPERNICUS_GLO30"
cop_dir.mkdir(parents=True, exist_ok=True)
(cop_dir / "sample_tiles").mkdir(exist_ok=True)

cop_guide = """# Copernicus DEM GLO-30 (Global 30m Elevation Model)

## 1. Overview & Relevance to DepthWizard
- **Relevance**: Copernicus GLO-30 provides worldwide coverage at 30-meter posting (derived from TanDEM-X radar interferometry). It offers superior vertical accuracy (LE90 < 4 meters) compared to SRTM GL1, especially over high-latitude, mountainous, and coastal zones.
- **License**: Free and open for commercial and academic use worldwide.

## 2. Official Metadata & Direct Access
- **Source**: European Space Agency (ESA) & Airbus Defence and Space.
- **AWS Open Data Registry**: [https://registry.opendata.aws/copernicus-dem/](https://registry.opendata.aws/copernicus-dem/)
- **Direct S3 Bucket**: `s3://copernicus-dem-30m/` (Region: `eu-central-1`)
- **Direct HTTPS Endpoint**: `https://copernicus-dem-30m.s3.amazonaws.com/` (Public read, no AWS credentials required)

## 3. Direct Tile Access Pattern
Tiles are organized by 1x1 degree bounding boxes:
- Washington D.C. area:
  `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N38_00_W078_00_DEM/Copernicus_DSM_COG_10_N38_00_W078_00_DEM.tif`
- Ahmedabad / SAC area:
  `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N23_00_E072_00_DEM/Copernicus_DSM_COG_10_N23_00_E072_00_DEM.tif`

## 4. Placement
Save tiles into:
`X:\\DatasetsSIH 26175\\02_CALIBRATION_AND_DATUM_DEM\\COPERNICUS_GLO30\\sample_tiles\\`
"""
(cop_dir / "README.md").write_text(cop_guide, encoding="utf-8")


# 7. OpenTopography API Guide
ot_dir = BASE_DIR / "02_CALIBRATION_AND_DATUM_DEM" / "OpenTopography_API"
ot_dir.mkdir(parents=True, exist_ok=True)

ot_guide = """# OpenTopography Global DEM REST API Access

## 1. Overview
OpenTopography provides on-the-fly subsetting and GeoTIFF download for global DEMs (SRTM GL1 30m, SRTM GL3 90m, Copernicus GLO-30, ALOS World 3D 30m, NASADEM).

## 2. API Endpoint Specification
- **Base URL**: `https://portal.opentopography.org/API/globaldem`
- **Parameters**:
  - `demtype`: `SRTMGL1` (30m), `SRTMGL3` (90m), `COP30` (Copernicus 30m), `COP90` (Copernicus 90m), `AW3D30` (ALOS 30m)
  - `south`, `north`, `west`, `east`: Bounding box in decimal degrees WGS84
  - `outputFormat`: `GTiff`
  - `API_Key`: Your free OpenTopography API Key

## 3. Obtaining an API Key
1. Register a free account at: [https://portal.opentopography.org/myopentopo](https://portal.opentopography.org/myopentopo)
2. Navigate to "My Account" -> "Request an API Key".
3. Add the key to DepthWizard config or environment variable:
   ```bash
   export OPENTOPOGRAPHY_API_KEY="your_api_key_here"
   ```

## 4. Example API Call
```bash
curl -X GET "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=38.85&north=38.95&west=-77.08&east=-76.98&outputFormat=GTiff&API_Key=YOUR_KEY" \\
     -o "X:/DatasetsSIH 26175/02_CALIBRATION_AND_DATUM_DEM/COPERNICUS_GLO30/sample_tiles/copernicus_dc_sample.tif"
```
"""
(ot_dir / "README.md").write_text(ot_guide, encoding="utf-8")

print("Successfully wrote all auxiliary guides and directory trees.")
