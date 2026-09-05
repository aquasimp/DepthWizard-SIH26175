# Data Sources and Attribution

## 1. GAMUS (Ground-Aerial Multimodal Urban Sensing)
- **Source**: Earthflow / EarthNets / RSI-MMSegmentation
- **Repository**: https://huggingface.co/datasets/earthflow/GAMUS
- **License**: Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Attribution Statement**:
  > GAMUS dataset provided by Earthflow. Published under CC-BY-4.0. Used for training and evaluating DepthWizard's single-view height estimation module.
- **Data Properties**:
  - GSD: 0.33 m/px
  - Spatial extent: 1024x1024 px tiles
  - RGB imagery co-registered with LiDAR-derived normalized Digital Surface Models (nDSM, above-ground height in metres)
  - Split convention: Official splits across Washington DC, New York City, and Philadelphia.

## 2. Shuttle Radar Topography Mission (SRTM) GL1 30 m DEM
- **Source**: NASA / USGS / OpenTopography
- **Coverage**: Global land coverage between 60°N and 56°S
- **Resolution**: 1 arc-second (~30 m at equator)
- **Vertical Datum**: EGM96 Geoid
- **License**: Public Domain / Open Data

## 3. Sample Evaluation Imagery (`data/samples/`)
- `sample_georeferenced.tif`: Orthorectified satellite imagery over Washington DC metropolitan area with UTM Zone 18N (EPSG:32618) projection, 0.33 m/px GSD.
- `sample_plain.png`: Standard non-georeferenced optical aerial photograph (PNG, no spatial metadata).
- `sample_unreferenced.tif`: Baseline optical aerial image stored in TIFF container without CRS or georeferencing transform.
- `sample_hilly.tif`: Orthorectified GeoTIFF showing elevation gradients and terrain variation.
