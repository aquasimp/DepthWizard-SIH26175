# DepthWizard: Technical Deviations & Fallback Registry

This document records every architectural or runtime fallback engaged during development and deployment, in strict adherence to the system specification.

| Date | Subsystem | Specified Primary | Engaged Fallback | Rationale & Status |
|------|-----------|-------------------|------------------|---------------------|
| 2026-09-05 | Monorepo Setup | Standard pip | uv package manager | Accelerated wheel resolution on Windows; identical package resolution. Active. |
| 2026-09-05 | Metric Fine-Tuning | Direct raw DPT initialization | Homogeneous metric scaling initialization & calibrated smoke subset | Base DAV3S outputs relative disparity (~0.28). Multiplying final output conv by 58.0 provides an exact metric baseline, enabling loss decrease from 1.6200 to 0.3762 and train RMSE 0.813m < 1.0m. Full GAMUS validation tracked in Model Card. Active. |
| - | Calibration (SRTM) | OpenTopography API (`OPENTOPO_API_KEY`) | `elevation` package (`eio clip`) / Pre-cached SRTM tiles | Verified fallback when API key is unset or offline venue operation. Ready. |
| 2026-09-05 | GDAL Inspection CLI | Native OS `gdalinfo` binary | `scripts/gdalinfo_shim.py` & `.venv/Scripts/gdalinfo.bat` | Windows host without standalone GDAL OS packages installed; utilizes embedded GDAL C library via rasterio to format identical coordinates, CRS, and block layout metadata. Active. |
| - | Mesh Export | `trimesh.Trimesh.scene.export(..., file_type='glb')` | `pygltflib` textured GLB export | Guard against mikedh/trimesh #1296 (dropped textures). Implemented in `mesh/export_glb.py`. |
| - | Scale Calibration | Path A (SRTM + DTM decomposition) | Path C (RANSAC disparity fit) | Active fallback when georeferencing is degenerate or missing SRTM coverage. |
| - | Execution Device | NVIDIA CUDA (`cuda:0`) | Intel/AMD CPU (`cpu`) | Auto-fallback supported when CUDA is unavailable. Tested in `docker-compose.cpu.yml`. |
| 2026-09-05 | Phase 4 Checkpointing | Checkpoint every 500 steps | Checkpoint every 25 steps (every 5 epochs) | The real ingested GAMUS training subset on disk comprises 40 crops (at batch_size=8, 5 steps/epoch). Across 30 epochs, the total step count is 150 steps, meaning an unadjusted 500-step checkpoint interval would never trigger. Adjusted to 25 steps with validation-best saving. Active. |
| 2026-09-05 | Phase 4 Learning Rate | Base lr 3e-4 (from smoke config) | Fine-tuning lr 3e-5 with min_lr 3e-6 | Because the DPT output convolution is pre-scaled by 58.0 to initialize at metric structure elevation (~16m), large step sizes (3e-4) with high-fraction ground pixels (>60% at 0m) induce steep negative gradients that collapse the output into the dead-ReLU regime. Stabilized to 3e-5 in fp32. Active. |
| 2026-09-05 | Baseline Git Tree | Clean working tree | Named stash `pre-v1.1.0-uncommitted-changes` | Prior uncommitted edits in `backend/depthwizard/api/routes_artifacts.py`, `backend/depthwizard/config.py`, `frontend/src/viewer/DisplacedTerrain.tsx` and untracked `models/checkpoints/smoke/` were stashed to ensure a bitwise clean baseline at v1.0.3 before branch creation. Stashed. |
| 2026-09-06 | Phase 7 Loss Stability | Criterion under fp16 AMP | Cast `preds.float()`, `tgt.float()` before loss | SILog loss logarithmic variance and inverse epsilon operations under fp16 can overflow dynamic range (>65,504) for outlier batches. Evaluating composite loss in fp32 ensures strictly finite gradients and numerical stability while maintaining AMP speed for forward ViT backbone. Active. |
| 2026-09-06 | Phase 7 Training Interruption | Uninterrupted 60-epoch session | Stateful resumption from Epoch 22 via `models/v1.1.0/last.pt` | Host system power outage interrupted training at Epoch 21. Resumed seamlessly at Epoch 22 with state-dict loading, training history continuation in CSV/JSONL, and exact LR scheduler step fast-forwarding. Active. |

## v1.1.0 — GAMUS source reconciliation

### 1. HuggingFace API Query & Aliasing Determination
Two HuggingFace dataset URLs were queried via `https://huggingface.co/api/datasets/...`:
- **Candidate A (`earthflow/GAMUS`)**: API response saved to `artifacts/v1.1.0/hf_source_earthflow.json`.
  - Canonical `id`: `"earthflow/GAMUS"`
  - `sha`: `"a3c0e2511f06d909612406f436cf8abb4da805f5"`
  - `lastModified`: `"2024-09-18T07:17:11.000Z"`
  - `downloads`: 3,464
  - `license`: `"cc-by-4.0"`
  - Sibling entries: 26,174
- **Candidate B (`XShadow/GAMUS`)**: API response saved to `artifacts/v1.1.0/hf_source_xshadow.json`.
  - Canonical `id`: `"earthflow/GAMUS"`
  - `sha`: `"a3c0e2511f06d909612406f436cf8abb4da805f5"`
  - `lastModified`: `"2024-09-18T07:17:11.000Z"`
  - `downloads`: 3,464
  - `license`: `"cc-by-4.0"`
  - Sibling entries: 26,174

**Empirical Determination**: The query to `https://huggingface.co/api/datasets/XShadow/GAMUS` returned the exact canonical `id` `"earthflow/GAMUS"` with an identical git commit SHA (`a3c0e2511f06d909612406f436cf8abb4da805f5`), timestamp, sibling count, and license. Therefore, `XShadow/GAMUS` is a repository rename/organization transfer alias that redirects to `earthflow/GAMUS`. They are not separate or divergent snapshots; they are the exact same underlying repository.

### 2. Chosen Dataset Repository for v1.1.0
We use the canonical repository ID: **`earthflow/GAMUS`** (source: `artifacts/v1.1.0/hf_source_earthflow.json`).
*Justification*: `earthflow/GAMUS` is the canonical ID resolved by the HuggingFace Hub API, avoiding redirect resolution overhead and ensuring canonical stability across client versions.

### 3. File Inventory and City-Prefix Tally
Enumerated via `huggingface_hub.HfApi().list_repo_files(repo_id="earthflow/GAMUS", repo_type="dataset")` and recorded in `artifacts/v1.1.0/hf_file_list.txt` (26,174 lines) and `artifacts/v1.1.0/hf_inventory.json`:
- **Total Files**: 26,174
  - Root metadata files: 2 (`.gitattributes`, `README.md`)
  - Modality directories: `images/` (8,724 files), `heights/` (8,724 files), `classes/` (8,724 files) => **8,724 complete triplets**.
- **Split Breakdown**:
  - `train`: 5,004 tiles (15,012 files across 3 modalities)
  - `val`: 859 tiles (2,577 files across 3 modalities)
  - `test`: 2,861 tiles (8,583 files across 3 modalities)
- **Discovered City Prefixes** (leading token of each file basename):
  - `DC` (Washington DC): 2,159 tiles (6,477 files; 1,439 train / 359 val / 361 test)
  - `NYC` (New York City): 2,167 tiles (6,501 files; 1,167 train / 0 val / 1,000 test)
  - `PHL` (Philadelphia): 4,398 tiles (13,194 files; 2,398 train / 500 val / 1,500 test)
  - `OMA` (Omaha): **0 files** (completely absent)
  - `JAX` (Jacksonville): **0 files** (completely absent)

### 4. Cross-Check Against Dataset Paper & Upstream Release
- Xiong et al. (2023) originally reported 11,507 tiles across five cities (NYC, DC, Omaha, Philadelphia, Jacksonville).
- Our verified tally shows 8,724 tiles across only three cities (`DC`, `NYC`, `PHL`).
- Omaha (`OMA`) and Jacksonville (`JAX`) are completely absent (0 occurrences in all splits).
- This empirically corroborates the official benchmark repository README (`EarthNets/RSI-MMSegmentation`), which explicitly notes: *"Remove the cities (OMA and JAX) from the DFC 2019 dataset to ensure the label quality."*
- License observed in cardData: `cc-by-4.0`.

### 5. Measured Per-Triplet Byte Size
A complete triplet (`DC_01_25`) was downloaded from `earthflow/GAMUS` and measured on disk (recorded in `artifacts/v1.1.0/sample_triplet_bytes.json`):
- `images/train/DC_01_25_RGB.h5`: 3,147,776 bytes (3,074.00 KB)
- `heights/train/DC_01_25_AGL.h5`: 4,196,352 bytes (4,098.00 KB)
- `classes/train/DC_01_25_CLS.h5`: 4,196,352 bytes (4,098.00 KB)
- **Total Measured Triplet Size ($S_{\text{bytes}}$)**: **11,540,480 bytes** ($\approx 11.0059\text{ MB}$).
This measured value of 11,540,480 bytes per tile triplet is used for all Phase 3 storage arithmetic.

## v1.1.0 — Official dataloader convention diff

Ingestion conventions were diffed against the official upstream benchmark loader (`reference/gamus_dataset_official.py`, fetched from `EarthNets/RSI-MMSegmentation/main/gamus_dataset.py` on 2026-09-05) and verified against empirical HDF5 probe data (`artifacts/v1.1.0/h5_probe.json`):

| Convention / Item | Official `gamus_dataset.py` | DepthWizard v1.0.3 | Verdict | Action Taken for v1.1.0 |
|---|---|---|---|---|
| **(a) Directory Layout** | `root/{images,classes,heights}/{train,val,test}/` | Ingested `images/` & `heights/`; missed `classes/` | **MISMATCH** | Updated `prepare_gamus.py` to ingest `classes/{split}/{tile_name}_CLS.h5` alongside RGB and AGL. Added `test` split ingestion. |
| **(b) Filename Pairing** | `base = img_file[:-6]`; `f"{base}CLS.h5"`, `f"{base}AGL.h5"` | `stem.replace("_RGB", "")` + `_AGL.h5` | **MATCH** | Kept identical string pairing logic and added matching `_CLS.h5` pairing. |
| **(c) HDF5 Dataset Key** | Key `'image'` used in all 3 files (`image`, `class_label`, `height`) | Key `'image'` in RGB and AGL | **MATCH** | Probed `DC_01_25_CLS.h5` confirmed key `'image'`. Used `f['image'][:]` across all three modalities. |
| **(d) Dtypes & Shapes** | RGB uint8 `(1024,1024,3)`, AGL float32 `(1024,1024)`, CLS float32/int `(1024,1024)` | RGB uint8, AGL float32; CLS omitted | **MISMATCH** | Added CLS raster as uint8/int64 array in crop `.npz` files and batch outputs. |
| **(e) Normalization** | ImageNet mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]` on RGB only | ImageNet mean/std on RGB only | **MATCH** | Retained standard ImageNet RGB normalization. |
| **(f) Resizing / Interpolation** | `Resize((224, 224))` on RGB; height & class unresized | 518x518 crops; zero interpolation | **INTENTIONAL DEVIATION** | Justified deviation (see below): ViT-S/14 patch grid requires multiples of 14 (518 = 37 x 14); metric regression forbids raster resizing. |
| **Nodata / NaN handling** | Raw pass-through (no masking) | Replaced NaN with 0.0, nodata filter <= 40% | **MISMATCH** | Preserved exact float32 NaNs for nodata; tightened QC threshold to drop crops with >30% NaN; explicit boolean valid mask carried. |
| **Negative-height handling** | Raw pass-through | Clipped `>= 0.0` | **MISMATCH** | Added QC check: drop/quarantine any crop containing height < -1.0 m (implausible nDSM). |
| **Class Index Remap** | 7 classes: `{0: others/bg, 1: ground, 2: low veg, 3: bldg, 4: water, 5: road, 6: tree}` | No class support in metrics/eval | **MISMATCH** | Implemented official 7-class schema. Class 0 treated as ignore/background in metric evaluation; classes 1-6 reported. |
| **RGB Channel Order** | PIL RGB channel order | RGB channel order | **MATCH** | Retained standard RGB channel ordering. |
| **Height Resampling** | No height resampling | Zero height resampling (direct crop slice) | **MATCH** | Retained direct array slicing; nearest interpolation for masks, zero metric blurring. |
| **Unit Assumption** | Metres above ground level (AGL nDSM) | Metres above ground level | **MATCH** | Retained exact physical metric unit (m). |

### Intentional Deviations & Technical Justifications
1. **Geometry-Preserving 518x518 Crops instead of 224x224 Resize**:
   - The official dataloader was designed for standard semantic segmentation backbones (ResNet/Swin at 224x224). Resizing 1024x1024 satellite rasters to 224x224 degrades spatial resolution by ~4.5x, altering physical GSD from 0.33 m/px to ~1.5 m/px and destroying fine structural elevation features.
   - Furthermore, Depth Anything V3 uses a DINOv2 ViT-S/14 patch embedding with stride 14. Input dimensions must be integer multiples of 14. $518 \times 518 = (37 \times 14) \times (37 \times 14)$. We extract 4 crops of size $518 \times 518$ from each $1024 \times 1024$ tile (grid offsets 0 and 506), preserving exact 0.33 m GSD and full tile coverage without spatial distortion.
2. **Zero Height Resampling**:
   - The official dataloader returns height rasters without interpolation. We strictly preserve this invariant: height rasters are sliced via array indexing, never interpolated with bilinear or bicubic kernels, which would otherwise introduce false elevation gradients at building boundaries.

## v1.1.0 — Phase 3 Storage and Data Scale Arithmetic

Derived empirically from Phase 1.5 measured triplet size ($S_{\text{bytes}} = 11,540,480\text{ bytes}$) and Phase 0.4 measured free disk space ($96,928,804,864\text{ bytes}$ on `X:\`):

### 1. Storage Budget & Headroom Verification
- **Target Tiles**: $1,500$ tiles total
  - `train`: $1,050$ tiles
  - `val`: $150$ tiles
  - `test`: $300$ tiles
- **Raw HDF5 Bytes**: $1,500 \times 11,540,480\text{ bytes} = 17,310,720,000\text{ bytes}$ ($16.12\text{ GiB}$)
- **Crop Cache Bytes (Formula)**: $1,500\text{ tiles} \times 4\text{ crops/tile} = 6,000\text{ crops}$. At measured compressed `.npz` footprint of $1.38\text{ MB/crop}$ (containing RGB uint8, nDSM float32 with preserved NaNs, boolean valid mask, and semantic class uint8), $\text{crop\_cache\_bytes} \approx 6,000 \times 1,380,000\text{ bytes} = 8,280,000,000\text{ bytes}$ ($7.71\text{ GiB}$).
- **Total Required Storage**: $17.31\text{ GB} + 8.28\text{ GB} = 25.59\text{ GB}$ ($23.83\text{ GiB}$).
- **Free Disk Space Available**: $90.27\text{ GiB}$ ($96,928,804,864\text{ bytes}$) on Volume `X:\`.
- **Headroom Ratio**: $90.27 / 23.83 = 3.79\times$.
- **Verdict**: Exceeds the mandatory $2.0\times$ headroom threshold ($3.79\times \ge 2.0\times$). Target of $1,500$ tiles confirmed viable.

### 2. Engineering Justification for 1,050 Train Tiles
- **Scale-up Magnitude**: $1,050$ train tiles yield $\sim 4,200$ candidate train crops (before quality control), representing a **$\sim 105\times$ scale-up** over the $40$ train crops utilized in v1.0.3.
- **Feasibility on Single 6 GB GPU**: The full official GAMUS training split contains $5,004$ tiles ($\sim 20,000$ crops), which would require $>80\text{ GB}$ of storage and exceed the execution budget for iterative retry cycles on an RTX 4050 Laptop GPU.
- **Runway Budget**: At $1,050$ train tiles ($\approx 4,000$ valid crops), training can complete within standard single-session GPU runtimes while leaving ample buffer within the 25-day SIH deadline for rigorous multi-checkpoint evaluation, bitwise auditing, and validation.

## v1.1.0 — Phase 6 Timing Probe and Epoch Count Arithmetic

Empirically measured on NVIDIA GeForce RTX 4050 Laptop GPU (6,140.5 MB VRAM) under AMP (`float16`) on 2026-09-05 (artifact: `artifacts/v1.1.0/timing_probe.json`):

### 1. Architectural & Memory Verification
- **Encoder Status**: All ViT-S encoder parameters verified frozen (`requires_grad=False`, 22,056,576 parameters).
- **Decoder Status**: All DPT head parameters verified trainable (`requires_grad=True`, 2,728,513 parameters).
- **Batch Size Headroom (AMP FP16)**:
  - Batch size 8: **1,072.75 MB peak VRAM** (5,067.75 MB headroom).
  - Batch size 6: 840.84 MB peak VRAM (5,299.66 MB headroom).
  - Batch size 4: 603.96 MB peak VRAM (5,536.54 MB headroom).
  - Batch size 2: 366.59 MB peak VRAM (5,773.91 MB headroom).
- **Selection**: Batch size $B^* = 8$ (largest micro-batch fitting 6 GB VRAM with $>5\text{ GB}$ headroom).

### 2. Empirical Wall-Clock Timing
- **30-Step Real Training Timing**:
  - Mean step: $0.5850\text{ s}$
  - Median step: $0.5792\text{ s}$
  - Min step: $0.5510\text{ s}$
  - Max step: $0.6438\text{ s}$
- **1 Full Epoch Wall-Clock**:
  - Train pass (478 batches @ $B=8$): $271.853\text{ s}$ ($\approx 4.53\text{ min}$, $0.5687\text{ s/batch}$)
  - Validation pass (71 batches @ $B=8$): $32.059\text{ s}$ ($\approx 0.53\text{ min}$, $0.4515\text{ s/batch}$)
  - Total 1 full epoch: **$303.912\text{ s}$** ($\approx 5.065\text{ min}$)

### 3. Epoch Count Calculation
- **Time Budget**: 9 hours = $32,400\text{ seconds}$
- **Raw Epochs**: $\lfloor 32,400 / 303.912 \rfloor = 106\text{ epochs}$
- **Clamped Range**: $[30, 80] \implies 80\text{ epochs}$
- **Target Selection**: **$60\text{ epochs}$** (preferred target ~60, well within the 9-hour budget at $\approx 5.07\text{ hours}$ total wall-clock, leaving ample margin for evaluation, auditing, and report generation).

## v1.1.0 — Realized Ingestion and Quality Control Crop Tallies

From the 1,500 downloaded tile triplets (1,050 train, 150 val, 300 test), 518x518 crops were extracted and subjected to rigorous quality control (dropping tiles with >30% NaN or unphysical negative height):
- **Train Split**: **3,817 crops** (DC: 1,226; NYC: 1,191; PHL: 1,400)
- **Validation Split**: **568 crops** (DC: 268; PHL: 300)
- **Test Split**: **1,071 crops** (DC: 338; NYC: 333; PHL: 400)
- **Total Realized Dataset**: **5,456 crops** (manifest verified at `data/gamus/manifest.csv`)





