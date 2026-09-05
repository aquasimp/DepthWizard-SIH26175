# DepthWizard 🧙‍♂️
### Single-View Height Estimation and 3D Flythrough
**Smart India Hackathon 2026 — Problem Statement 26175 (ISRO / SAC)**

DepthWizard converts a **single optical RGB remote-sensing image** into a high-precision Digital Surface Model (DSM) and provides an interactive, browser-based 3D flythrough environment with height probing, slope analysis, and reference validation.

---

## 🏗️ System Architecture

```
+-------------------------------------------------------------------------+
|                  Single-View Optical Remote Sensing Input               |
|                       (GeoTIFF / TIFF / PNG / JPG)                      |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|     Georeferencing & Transform Detector (io/detect.py, io/gsd.py)       |
|    - Georeferenced (GeoTIFF): Metric normalization to 0.33 m/px GSD     |
|    - Non-Georeferenced (PNG/JPG): Assumed 0.33 m/px GSD normalization   |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|     Seamless Tiled Inference Engine (depth/infer.py, depth/tiling.py)   |
|    - Depth Anything V2 Small Backbone (DINOv2 ViT-S + DPT Head)         |
|    - 512px sliding tiles with 64px overlap & cosine-feathered blending  |
|    - Overlap region median matching to eliminate tile boundary drift    |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|            Scale Calibration Decision Engine (calibration/)             |
|    - Path A: SRTM GL1 30 m DTM Decomposition (EGM96 Vertical Datum)     |
|    - Path B: Ground Control Point (GCP) Quadratic Huber Surface Fit     |
|    - Path C: RANSAC Affine Disparity Alignment with Degeneracy Guard    |
|    - Path D: Relative Unitless Normalization [0, 1]                     |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|           Geospatial Exporters & 3D Mesh Generator (mesh/, io/)         |
|    - Standard GeoTIFF DSM (float32, LZW, EGM96) & metric nDSM           |
|    - 16-bit PNG Heightmap with linear decoding sidecar meta.json        |
|    - Three LOD Binary GLBs with identity UV texture mapping             |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|            Interactive 3D Web Viewer & Validation Platform              |
|    - Three.js / React Three Fiber PBR Displaced Terrain Canvas          |
|    - First-Person Flythrough Controls (WASD, pointer lock)              |
|    - Real-Time Height Probe & Angular Slope Analysis Overlay            |
|    - Synchronized Dual-Camera Validation & Error Heatmaps               |
+-------------------------------------------------------------------------+
```

---

## ⚡ Quickstart

### Option 1: Docker (Single Command)
```bash
# Clone the repository
git clone https://github.com/depthwizard/depthwizard.git
cd depthwizard

# Launch application (NVIDIA GPU supported)
docker compose up --build
```
Access the application at **`http://localhost:8080`**.

For CPU-only machines:
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build
```

### Option 2: Local Development Setup
```bash
# Setup Python virtual environment & frontend dependencies
make setup

# Run backend and frontend development servers
make dev
```

---

## 📊 Evaluation Summary

Evaluated against all 16 held-out validation crops from the GAMUS dataset (4.29M pixels) with airborne LiDAR reference data:

| Region / Stratum | Bias (ME) [m] | MAE [m] | RMSE [m] | LE90 [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|------------------|---------------|---------|----------|----------|-------------|------------------------|------------------------|
| **Washington DC** | +1.65 | 11.58 | 12.93 | 17.65 | -0.116 | 3.6% | 9.1% |
| **Philadelphia** | +14.85 | 14.85 | 14.98 | 16.93 | 0.500 | 0.0% | 0.0% |
| **Overall Held-Out** | +8.26 | 13.22 | 14.00 | 17.24 | 0.089 | 1.8% | 4.5% |
| Ground (<0.5m) | +16.00 | 16.00 | 16.04 | 17.39 | 0.025 | 0.0% | 0.0% |
| Low Canopy (0.5–3m) | +14.72 | 14.72 | 14.79 | 16.45 | 0.110 | 0.0% | 0.0% |
| Mid-Rise (3–15m) | +10.68 | 10.69 | 11.35 | 14.77 | -0.152 | 0.7% | 3.3% |
| Tall Structures (≥15m) | -10.33 | 10.49 | 12.34 | 19.01 | 0.040 | 6.9% | 15.6% |

---

## 📜 Licenses & Attribution

- **DepthWizard Software Suite**: Licensed under the [MIT License](LICENSE).
- **Depth Anything V2 Small**: Licensed under the **Apache License 2.0**.
  - Reference: *Depth Anything V2*, Yang et al., 2024.
- **GAMUS Dataset**: Licensed under **Creative Commons Attribution 4.0 International (CC-BY-4.0)**.
  - Attribution: *GAMUS: A Ground-Aerial Multimodal Urban Sensing Dataset for 3D City Modeling*, Earthflow / RSI-MMSegmentation.
- **SRTM 30 m DEM**: Courtesy of NASA / USGS / OpenTopography (Public Domain).
