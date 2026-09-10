# DepthWizard — Complete Architectural Blueprint & In-Depth Technical Specification
## Smart India Hackathon 2026 · Problem Statement 26175 (ISRO / Space Applications Centre)
**Project**: DepthWizard — Single-View Height Estimation and 3D Interactive Flythrough  
**Version**: v1.1.0 Multi-City Scale  
**Classification**: Technical Architecture & System Blueprint

---

## 1. Executive Summary & Problem Context

### 1.1 The Operational Challenge (ISRO / Space Applications Centre)
In modern Earth observation, intelligence reconnaissance, and disaster response, generating 3D surface elevation (Digital Surface Models — DSMs) is essential for:
- Calculating flood inundation and storm surge boundaries.
- Urban infrastructure planning and building volume estimation.
- Military mission rehearsal, line-of-sight analysis, and low-altitude flight navigation.

Historically, 3D elevation data requires either:
1. **Multi-View Stereophotogrammetry**: Sourcing two overlapping satellite images captured from different orbital angles. This requires multiple satellite passes, cloud-free optical windows, and computationally intensive semi-global matching (SGM).
2. **Airborne LiDAR**: Highly precise laser scanning that costs thousands of dollars per flight hour, is constrained by airspace regulations, and cannot be operated in hostile, denied, or disaster-struck regions.

**SIH Problem Statement 26175** poses a transformative objective:
> **Predict metric surface elevation directly from a single optical aerial or satellite RGB image and generate an interactive 3D flythrough environment in real time.**

---

## 2. System Architecture & High-Level Component Topology

DepthWizard is built as a clean, production-grade micro-architecture decoupled into five major subsystems:

```mermaid
graph TD
    subgraph Client ["Frontend Client (React 18 + Vite + Three.js)"]
        UI["Upload & Job Dashboard"]
        Viewer["3D WebGL Flythrough Canvas"]
        HUD["Viewer HUD & Flight Telemetry"]
        Tool["3D Spatial Measure & Slope Analysis"]
    end

    subgraph API ["Application & Job Management Layer (FastAPI)"]
        Routes["REST Endpoints (/api/jobs, /api/health, /api/validate)"]
        JobMgr["Asynchronous Job Orchestrator & State Machine"]
        Storage["Artifact Store (jobs/<job_id>/)"]
    end

    subgraph AI ["Computer Vision & AI Inference Engine (PyTorch)"]
        DINO["DINOv2-S Vision Transformer Backbone (Frozen 175 Tensors)"]
        DPT["Dense Prediction Transformer Multi-scale Decoder"]
        Ensemble["Adaptive Dual-Head Ensemble (best.pt + best_tall.pt)"]
    end

    subgraph Calib ["Geodetic Calibration Engine (Paths A - D)"]
        PathA["Path A: In-Scene GCPs / LiDAR Huber RANSAC"]
        PathB["Path B: Spaceborne DEM Co-registration (Copernicus GLO-30 / SRTM)"]
        PathC["Path C: GSD & Solar Trigonometry"]
        PathD["Path D: Self-Contained 16-Bit Normalization"]
    end

    subgraph Geometry ["3D Geometry & GIS Exporter"]
        Tiling["Vectorized Quad Triangulation"]
        Decim["Quadric Error Decimation (LOD0, LOD1, LOD2)"]
        GLB["Self-Contained Textured GLB Binary Builder"]
        GeoTIFF["Cloud-Optimized GeoTIFF Exporter (DSM / nDSM / rDSM)"]
    end

    UI -->|Multipart POST /api/jobs| Routes
    Routes --> JobMgr
    JobMgr --> AI
    AI --> Calib
    Calib --> Geometry
    Geometry --> Storage
    Storage -->|GeoTIFF, 16-bit PNG, GLB| Viewer
    Viewer --> HUD
    Viewer --> Tool
```

---

## 3. The Deep Learning Engine & Architectural Innovations

### 3.1 Foundational Backbone: DINOv2-S
DepthWizard leverages Meta’s **DINOv2 Small (`vits/14`)** vision transformer foundation model as its visual backbone:
- **Patch Embedding**: Converts an input image into non-overlapping $14 \times 14$ pixel patches.
- **Canonical Grid Dimension**: An input resolution of $518 \times 518$ pixels yields an exact integer grid of $37 \times 37 = 1,369$ visual tokens ($518 / 14 = 37$).
- **Frozen Backbone Guarantee**: All 175 weight tensors of the DINOv2 backbone remain bitwise frozen during training (`max_abs_diff == 0.0`). This guarantees that the pre-trained visual semantics, illumination invariance, and structural reasoning learned across hundreds of millions of images are permanently preserved without catastrophic forgetting.

### 3.2 Dense Prediction Transformer (DPT) Head
Standard convolutional decoders produce blurry building contours. DepthWizard uses a **DPT multiscale reassembly neck**:
1. Intermediate feature representations are extracted from four transformer layers: Layer 3 ($1/4$ resolution), Layer 6 ($1/8$ resolution), Layer 9 ($1/16$ resolution), and Layer 12 ($1/32$ resolution).
2. Spatial Reassembly blocks project tokens into feature maps via $1 \times 1$ convolutions and transposed convolutions.
3. Residual Convolutional Units (RCUs) and feature fusion blocks iteratively merge coarse global context with sharp fine-grained edge details.

### 3.3 The Core Breakthrough: Adaptive Dual-Head Ensemble
Monocular elevation models suffer from an inherent statistical pathology: **height distribution long-tail suppression**. In typical urban terrain, $>90\%$ of pixels belong to ground, roads, and residential roofs ($<10\text{ m}$), while only $<3\%$ belong to tall commercial structures ($>20\text{ m}$). Training a single network with global loss causes it to underestimate high-rises to minimize global ground penalty.

DepthWizard resolves this with an **Adaptive Dual-Head Ensemble**:
- **Head A (`models/v1.1.0/best.pt`)**: Trained on 3,817 multi-city crops. Highly accurate on ground, roads, and residential structures (MedAE $0.7084\text{ m}$).
- **Head B (`models/v1.1.0/best_tall.pt`)**: Specialized on high-relief structures, delivering a **46.2% error reduction** on high-rises $\ge 15\text{ m}$.
- **Mathematical Sigmoidal Fusion**:
  $$\hat{H}(u, v) = (1 - \alpha) \cdot H_{\text{base}}(u, v) + \alpha \cdot H_{\text{tall}}(u, v)$$
  where the spatial blending weight $\alpha(u, v)$ is smoothly computed from base prediction:
  $$\alpha(u, v) = \frac{1}{1 + \exp\left(-\frac{H_{\text{base}}(u, v) - 15.0}{3.0}\right)}$$
  - At $H \le 10\text{ m}$: $\alpha \to 0$ (guided 100% by the sub-metre base head).
  - At $H \ge 20\text{ m}$: $\alpha \to 1$ (guided 100% by the tall specialist head).
  - Transition is smooth ($\mathcal{C}^\infty$ continuous), preventing artificial seams or boundary cliffs.

### 3.4 The GAMUS Benchmark: Provenance, Quality Control & Geometry
The empirical backbone of DepthWizard’s fine-tuning is the **GAMUS (Global Aerial Mapping and Urban Surface Elevation)** research benchmark:
- **Scientific Provenance**: Authored by Xiong et al. (2023), *"GAMUS: A Dataset for Global Aerial Mapping and Urban Surface Elevation Estimation"*, hosted canonically on Hugging Face at [`earthflow/GAMUS`](https://huggingface.co/datasets/earthflow/GAMUS) (CC-BY 4.0 license).
- **Core Data Modalities**: Derived from the high-resolution IEEE GRSS Data Fusion Contest 2019 (DFC 2019). Comprises **8,724 complete triplets** across three major US metropolitan regions: Washington DC (`DC`), New York City (`NYC`), and Philadelphia (`PHL`):
  1. Optical high-resolution aerial RGB orthophotos (0.33 m/pixel GSD).
  2. Airborne LiDAR-derived metric Above Ground Level (AGL) nDSM height rasters.
  3. Ground-truth 7-class semantic land-cover segmentation maps.
- **Zero-Interpolation Spatial Cropping**: Standard semantic segmentation dataloaders downsample 1024×1024 tiles to 224×224, degrading physical GSD to ~1.5 m/px and blurring structural edges. DepthWizard implements a **geometry-preserving extraction**: extracting non-interpolated 518×518 crops matching the exact $37 \times 14 = 518$ token grid of DINOv2-S.
- **QC-Filtered Split Volume**: After automated QC (quarantining rasters with $>30\%$ nodata or negative heights), DepthWizard leverages **3,218 train crops**, **536 validation crops**, and **1,071 held-out test crops** (35,139,491 reference LiDAR pixels).

---

## 4. The 4-Tier Geodetic Calibration Engine

Monocular depth models predict relative disparity $d(u, v) \in [0, 1]$. To be operationally useful to ISRO/SAC, this must be converted into **true metric elevation ($H$) in metres anchored to sea level (EGM96 geoid)**:
$$H(u, v) = s \cdot d(u, v) + t$$

DepthWizard implements an automated **4-Tier Calibration Hierarchy** orchestrated by `selector.py` with automatic fallback ($B \to A \to C \to D$):

### Path B: In-Scene Ground Control Points (GCPs) / LiDAR Samples (`gcp_fit.py`, `ransac_fit.py`)
- **Applicability**: When surveyed Ground Control Points (GCPs) or reference airborne LiDAR samples ($\ge 3$ non-collinear points) are provided.
- **Methodology**: 
  - Validates singular value decomposition (SVD) condition number to reject collinear degenerate GCP configurations.
  - Fits scale $s$ and translation $t$ using **Huber Regressor Loss**, immune to extreme outlier measurement noise.

### Path A: Spaceborne DEM Co-registration & DTM Decomposition (`srtm.py`, `dtm_decompose.py`, `co_register.py`)
- **Applicability**: Georeferenced GeoTIFF input with valid CRS and bounding coordinates.
- **Methodology**:
  1. Automatically queries cached or online spaceborne DEMs (NASA SRTM 30m / Copernicus GLO-30) over the scene bounding box.
  2. Applies morphological disk filtering (`decompose_bare_earth_dtm`) to separate bare-earth terrain (DTM) from structures.
  3. Computes terrain slope; safely transitions to Path C if scene exhibits extreme steepness ($>45^\circ$) or building density exceeds $80\%$.
  4. Anchors the surface to the EGM96 geoid via median elevation matching and sub-pixel cross-correlation (`co_register.py`).

### Path C: Disparity RANSAC Affine Alignment (`ransac_affine.py`, `ransac_fit.py`)
- **Applicability**: Georeferenced scenes lacking spaceborne tiles, or scenes rejected by Path A terrain guards.
- **Methodology**:
  - Implements **RANSAC Huber Regressor** scale-shift estimation against reference elevation priors.
  - Includes a strict **Degeneracy Guard**: detects flat terrain or water bodies where disparity variance $\sigma^2 < 10^{-4}$, safely providing stable default scaling without NaN division.

### Path D: Self-Contained 16-Bit Relative Normalization (`relative.py`)
- **Applicability**: Unreferenced consumer imagery (JPEG/PNG) uploaded without spatial metadata.
- **Methodology**:
  - Quantizes disparity into a 16-bit unsigned integer range $[0, 65535]$.
  - Generates mathematical sidecar `heightmap.meta.json` recording minimum and maximum elevation boundaries:
    $$H_{\text{real}} = h_{\min} + \left(\frac{px}{65535}\right) \times (h_{\max} - h_{\min})$$

---

## 5. End-to-End Processing Pipeline Lifecycle

When an image is submitted to `/api/jobs`, the system executes an automated six-stage state machine:

```
[UPLOAD] ──> [PREPROCESS] ──> [INFER] ──> [CALIBRATE] ──> [EXPORT] ──> [MESH] ──> [DONE]
```

1. **STAGE 1 — PREPROCESS (Progress: 10%)**:
   - Inspects image headers via `rasterio` to detect CRS, affine transform, and GSD.
   - Converts multi-band imagery to canonical RGB.
   - Pads or scales image to compatible patch dimensions ($518 \times 518$ grid).
2. **STAGE 2 — INFER (Progress: 40%)**:
   - Executes PyTorch GPU inference using the selected model architecture.
   - For images larger than $518 \times 518$, runs an overlapping sliding-window tiler with 2D Hann-window cosine cross-fading to eliminate tile seams.
3. **STAGE 3 — CALIBRATE (Progress: 65%)**:
   - Runs DTM (Digital Terrain Model) morphological opening to separate ground from structures.
   - Executes Calibration Hierarchy (Paths A-D).
   - Generates absolute DSM and normalized nDSM arrays.
4. **STAGE 4 — EXPORT (Progress: 78%)**:
   - Writes georeferenced `dsm.tif` and `ndsm.tif` with LZW compression and tiling.
   - Encodes `heightmap_16bit.png` and writes `heightmap.meta.json`.
5. **STAGE 5 — MESH (Progress: 88%)**:
   - Executes vectorized grid triangulation to create 3D surface vertices, triangles, and UV coordinates.
   - Generates three decimated Levels of Detail (LOD0: 100%, LOD1: 50%, LOD2: 25%).
   - Embeds the aerial color texture into self-contained binary `terrain_lod0.glb`, `lod1.glb`, and `lod2.glb` files.
6. **STAGE 6 — DONE (Progress: 100%)**:
   - Records metadata, inference execution times, and accuracy telemetry into `status.json`.

---

## 6. Frontend & Interactive 3D WebGL Visualization

The frontend client is built with **React 18**, **TypeScript**, **Vite**, and **Three.js / WebGL**, featuring:

### 6.1 Dual 3D Rendering Modes
- **Mode A: Dynamic GPU Shader Displacement (`DisplacedTerrain.tsx`)**:
  - Reads `heightmap_16bit.png` directly into GPU memory as an unsigned texture.
  - A custom GLSL vertex shader displaces vertices along the Y-axis in real time.
  - Recalculates analytical normals on the GPU every frame, enabling instant slider changes for **Vertical Exaggeration** ($0.5\times - 3.0\times$) without regenerating 3D geometry.
- **Mode B: Multi-LOD Textured Mesh Streaming (`GlbTerrain.tsx`)**:
  - Loads binary `.glb` files with embedded JPEG textures and pre-computed vertex normals.
  - Ensures a locked **60 FPS flythrough** on any consumer laptop or mobile device.

### 6.2 Tactical Pilot & Analysis Controls
- **3 Camera Flight Rigs**:
  - *Orbit Camera*: Traditional turntable inspection for rotating around buildings.
  - *Fly Camera*: First-person drone flight simulator with WASD and mouse-look.
  - *Top Camera*: Orthographic overhead map mode for planning and measurement.
- **Dynamic Solar Simulation**:
  - Real-time directional lighting controlled by **Azimuth** ($0^\circ - 360^\circ$) and **Elevation** ($0^\circ - 90^\circ$) sliders to visualize diurnal shadows.
- **Slope Hazard Analysis Mode**:
  - Real-time shader color-ramp: Green (flat ground $<10^\circ$), Yellow (moderate slope $10-30^\circ$), Red (steep incline / vertical building wall $>30^\circ$).
- **3D Measurement Tool**:
  - Interactive spatial raycasting allowing users to click two points on the 3D terrain to measure 3D Euclidean distance, horizontal distance, and vertical building height.

---

## 7. Comprehensive Directory & File Structure

```
DepthWizard SIH26175/
├── backend/
│   └── depthwizard/
│       ├── __init__.py               # Version 1.1.0 declaration
│       ├── config.py                 # System paths, GPU flags, default checkpoints
│       ├── main.py                   # FastAPI app entry point & /api/health
│       ├── api/
│       │   ├── routes_jobs.py        # POST /api/jobs, GET /api/jobs/{id}
│       │   ├── routes_artifacts.py   # GET /api/jobs/{id}/artifacts/{file}
│       │   └── routes_validate.py    # POST /api/validate (Ground-truth split-screen)
│       ├── depth/
│       │   ├── infer.py              # DepthInferenceEngine & Adaptive Dual-Head Ensemble
│       │   ├── backbone.py           # DINOv2-S ViT-Small backbone (frozen 175 tensors, 24.8M params)
│       │   ├── head.py               # Dense Prediction Transformer multiscale decoder head
│       │   └── tiling.py             # 2D Hann-window cosine cross-fading sliding tiler
│       ├── calibration/
│       │   ├── selector.py           # Automated 4-tier calibration path selector (B -> A -> C -> D)
│       │   ├── srtm.py               # Spaceborne SRTM 30m DEM tile fetcher & reprojector
│       │   ├── dtm_decompose.py      # Path A: Morphological disk bare-earth terrain decomposition
│       │   ├── gcp_fit.py            # Path B: Ground Control Point (GCP) Huber regression
│       │   ├── ransac_affine.py      # Path C: Disparity RANSAC affine alignment & degeneracy guard
│       │   ├── relative.py           # Path D: 16-bit integer relative disparity normalizer
│       │   └── datum.py              # Geodetic datum conversion utilities (EGM96 geoid anchoring)
│       ├── eval/
│       │   ├── coregister.py         # Phase cross-correlation sub-pixel grid alignment
│       │   ├── metrics.py            # Evaluation metrics (RMSE, MAE, MedAE, NMAD, LE90)
│       │   └── report.py             # Quantitative JSON/CSV performance reporter
│       ├── mesh/
│       │   ├── heightmap_to_mesh.py  # Vectorized grid triangulation
│       │   ├── export_glb.py         # Pygltflib binary GLB textured exporter
│       │   └── decimate.py           # Multi-LOD Quadric Error decimation
│       ├── io/
│       │   ├── writers.py            # GeoTIFF and 16-bit PNG heightmap encoders
│       │   ├── readers.py            # Rasterio / GDAL robust image loader
│       │   ├── detect.py             # CRS and georeferencing detector
│       │   └── gsd.py                # Canonical 0.33 m/px GSD normalizer
│       └── jobs/
│           ├── manager.py            # Thread-safe job store and status state machine
│           └── pipeline.py           # End-to-end 6-stage orchestration runner
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # Main routing, application shell, & backend health monitor
│   │   ├── components/
│   │   │   └── ControlHud.tsx        # Tactical flight telemetry, camera rigs, sun & LOD controls
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx        # Upload portal with real-time backend health detection
│   │   │   ├── ViewerPage.tsx        # 3D interactive flythrough cockpit with error guards
│   │   │   ├── JobStatusPage.tsx     # Real-time state machine progress monitor
│   │   │   └── ValidatePage.tsx      # Side-by-side LiDAR accuracy validator
│   │   └── viewer/
│   │       ├── DisplacedTerrain.tsx  # WebGL custom vertex shader displacement
│   │       ├── GlbTerrain.tsx        # Binary GLB textured mesh loader
│   │       ├── CameraRig.tsx         # Orbit, First-Person Fly (WASD), & Top camera rigs
│   │       ├── HeightProbe.tsx       # Real-time raycasted terrain elevation probe
│   │       └── MeasureTool.tsx       # 3D Euclidean distance and height measurement tool
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── models/
│   ├── depth_anything_v2_vits.pth    # Zero-shot base foundation weights (24.8M params)
│   └── v1.1.0/
│       ├── best.pt                   # Multi-city fine-tuned checkpoint (Epoch 48, Val RMSE 3.73m)
│       ├── best_tall.pt              # Tall-structure specialist head (Epoch 33, 46.2% error drop)
│       └── checkpoint_state.json     # Training epoch and validation metric state history
│
├── training/
│   ├── train_v110.py                 # GPU training script with FP32 composite loss
│   ├── dataset.py                    # PyTorch Dataset for GAMUS crops
│   ├── sampler.py                    # Height-stratified batch sampler
│   └── losses.py                     # SILog + L1 + Multiscale Gradient composite loss (MetricNDSMLoss)
│
├── scripts/
│   ├── prepare_gamus_v110.py         # Data QC, cropping, and manifest builder
│   ├── evaluate_v110.py              # Full 1,071 test crop quantitative evaluator
│   ├── audit_weights_v110.py         # Bitwise verification against foundation weights
│   ├── audit_v1.1.0_claims.py        # Independent claims and artifact auditor
│   └── test_live_inference_job.py   # Automated end-to-end API verification script
│
├── tests/
│   ├── test_api_e2e.py               # FastAPI endpoint lifecycle tests
│   ├── test_dataset_gamus.py         # Dataset manifest and crop batch tests
│   ├── test_mesh_geometry.py         # Mesh triangulation and UV boundary tests
│   ├── test_writers_geotiff.py       # Cloud-Optimized GeoTIFF raster tests
│   ├── test_coregister.py            # Sub-pixel phase cross-correlation tests
│   └── test_calibration_ransac.py    # Robust RANSAC fitting & degeneracy tests
│
└── docs/
    ├── DEPTHWIZARD_COMPREHENSIVE_BLUEPRINT.md
    ├── RELEASE_NOTES_v1.1.0.md
    ├── DEVIATIONS.md
    └── HACKATHON_WINNING_CRITERIA_AND_PITCH.md
```

---

## 8. Quantitative Benchmarks & Judge Review Defense

### 8.1 Training Convergence & Validation Metrics (536 Validation Crops)
During training on the multi-city GAMUS dataset, validation performance was logged after every epoch:
- **Checkpoint Selection**: The primary checkpoint (`models/v1.1.0/best.pt`) was captured at **Epoch 48**, attaining a **Validation RMSE of 3.7333 m** (with training RMSE of $5.8844\text{ m}$).
- **Tall-Structure Specialist Checkpoint**: The high-relief specialist (`models/v1.1.0/best_tall.pt`) was captured at **Epoch 33**, attaining a validation RMSE on structures $\ge 15\text{ m}$ of **7.7341 m**.
- Both checkpoints demonstrate smooth monotonic convergence without overfitting, verified by recorded loss curves in `docs/assets/v1.1.0_training_curves.png`.

### 8.2 Comprehensive Held-Out Test Evaluation (1,071 Held-Out Test Tiles, 35.1M Pixels)
To evaluate real-world generalization, the system was independently benchmarked on all **1,071 held-out test tiles** (comprising 35,139,491 valid reference pixels) across Washington DC, New York City, and Philadelphia:

| Benchmark Metric | DepthWizard v1.0.3 | DepthWizard v1.1.0 | Quantitative Gain |
| :--- | :---: | :---: | :--- |
| **Median Absolute Error (MedAE)** | `1.7133 m` | **`0.7084 m`** | **58.7% Error Reduction (Sub-metre!)** |
| **Root Mean Square Error (RMSE)** | `6.7508 m` | **`4.4672 m`** | **33.8% Overall Error Reduction** |
| **Mean Absolute Error (MAE)** | `3.9340 m` | **`2.3645 m`** | **39.9% Overall Error Reduction** |
| **Linear Error 90% (LE90)** | `10.8202 m` | **`6.8767 m`** | **36.4% Error Bound Reduction** |
| **Pearson Correlation ($r$)** | `0.5868` | **`0.8374`** | **+0.2506 Topographic Alignment** |
| **Precision ($\delta < 2.5\text{ m}$)** | `58.60%` | **`69.60%`** | **+11.00 Percentage Points** |
| **Tall Structures ($\ge 15\text{ m}$)** | `13.5844 m` | **`7.3037 m`** | **46.2% Error Reduction on High-Rises** |

> [!NOTE]
> **Validation vs. Test Metric Distinction**:
> - **Validation RMSE (3.73 m)**: Calculated across the 536 validation crops used for early stopping and hyperparameter monitoring.
> - **Test RMSE (4.47 m)**: Calculated across the entire 1,071 held-out test crops (35.1M pixels) under strict zero-leakage conditions.

---

## 9. Hardware Requirements & Operational Readiness

DepthWizard is engineered for zero-dependency execution across both high-performance field workstations and constrained field laptops:

### 9.1 Hardware Specifications
| Specification | Recommended (GPU Production) | Minimum (CPU Field Fallback) |
| :--- | :--- | :--- |
| **Processor** | 8-core modern x86_64 CPU (Intel i7/i9 or AMD Ryzen 7/9) | 4-core 64-bit CPU |
| **GPU / VRAM** | NVIDIA RTX 3060 / 4060 or higher (8 GB+ VRAM, CUDA 11.8 / 12.x) | None (Integrated GPU or Pure CPU) |
| **System RAM** | 16 GB DDR4/DDR5 | 8 GB RAM |
| **Disk Storage** | 2.5 GB available space (models + temporary cache) | 2.0 GB available space |
| **Inference Time** | **0.8 s – 1.5 s** per $518 \times 518$ scene | **4.0 s – 7.5 s** per scene (automatic CPU fallback) |

### 9.2 Offline Air-Gapped Operation
During live hackathon judging and field deployments:
- **No Internet Required**: All foundation and fine-tuned weights (`models/v1.1.0/best.pt`, `best_tall.pt`, `depth_anything_v2_vits.pth`) reside locally on disk.
- **Offline SRTM Cache**: Standard geographical tiles are pre-cached in `data/cache/srtm/`. If spaceborne DEMs for a remote bounding box are not pre-cached, the geodetic calibration engine automatically and gracefully engages **Path C (Huber RANSAC Disparity Fitting)** or **Path D (Self-Contained 16-Bit Relative Normalization)** without crashing or hanging.

---
**DepthWizard provides a complete, mathematically grounded, and production-tested solution for single-view satellite 3D reconstruction.**
