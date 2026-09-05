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

> **Headline Accuracy (Typical-Case):**
> - **Median Absolute Error (MedAE): 1.63 m** (reduced by 88.4% from 14.09 m zero-shot baseline)
> - **Sub-2.5m Accuracy ($\delta < 2.5\text{m}$): 60.9%** (~17× improvement from 3.48% baseline)
> - **Sub-1.0m Accuracy ($\delta < 1.0\text{m}$): 34.0%** (~30× improvement from 1.14% baseline)
>
> *Note on Overall RMSE (8.26 m):* Overall RMSE is 8.26 m (down from 14.00 m zero-shot, a 41% error reduction). This quadratic metric is pulled heavily upward by commercial high-rises in the Washington DC validation subset ($\ge 15\text{ m}$ structures, RMSE 15.11 m, bias -10.06 m), which are underrepresented in the 40-crop training sample. For typical ground, low canopy, and suburban terrain (the vast majority of pixels), MedAE (1.63 m) and regional metrics (Philadelphia RMSE 1.86 m, 87.6% sub-2.5m) reflect real-world performance.

| Region / Stratum | MedAE [m] (Headline) | $\delta < 2.5\text{m}$ (Headline) | MAE [m] | RMSE [m] (Tail-Sens.) | Bias (ME) [m] | LE90 [m] | Pearson $r$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Philadelphia (Suburban/Mid-Rise)** | **1.02** | **87.6%** | **1.32** | **1.86** | +0.44 | 2.78 | 0.635 |
| **Washington DC (Urban High-Rise)** | 5.01 | 34.0% | 8.12 | 11.55 | -4.16 | 21.46 | 0.577 |
| **Combined Held-Out Set (Fine-Tuned)** | **1.63** | **60.9%** | **4.71** | **8.26** | **-1.86** | **15.12** | **0.707** |
| *Pre-Training Zero-Shot Baseline (v1.0.1)* | *14.09* | *3.5%* | *13.22* | *14.00* | *+12.68* | *17.24* | *+0.089* |
| Ground (<0.5m) | 0.92 | 89.6% | 1.44 | 2.97 | +1.44 | 2.56 | 0.080 |
| Low Canopy / Structures (0.5–3m) | 0.89 | 87.3% | 1.67 | 3.61 | +0.86 | 2.93 | 0.082 |
| Mid-Rise Structures (3–15m) | 2.68 | 47.2% | 4.16 | 5.98 | -0.54 | 10.17 | 0.424 |
| Tall Structures (≥15m) | 10.66 | 14.2% | 12.24 | 15.11 | -10.06 | 25.32 | 0.132 |

---

## 📜 Licenses & Attribution

- **DepthWizard Software Suite**: Licensed under the [MIT License](LICENSE).
- **Depth Anything V2 Small**: Licensed under the **Apache License 2.0**.
  - Reference: *Depth Anything V2*, Yang et al., 2024.
- **GAMUS Dataset**: Licensed under **Creative Commons Attribution 4.0 International (CC-BY-4.0)**.
  - Attribution: *GAMUS: A Ground-Aerial Multimodal Urban Sensing Dataset for 3D City Modeling*, Earthflow / RSI-MMSegmentation.
- **SRTM 30 m DEM**: Courtesy of NASA / USGS / OpenTopography (Public Domain).
