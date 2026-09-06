# DepthWizard v1.1.0 Release Notes — "Data Quality & Scale-Up"

**Release Date**: September 6, 2026  
**Problem Statement**: Smart India Hackathon 2026 · PS 26175 (ISRO / Space Applications Centre)  
**Repository Branch**: `release/v1.1.0`  
**Base Foundation**: Depth Anything V2 Small (`vits` encoder + DPT metric head)

---

## 🚀 Key Highlights & Architectural Advancements

DepthWizard v1.1.0 represents a major milestone in single-view satellite and aerial metric height estimation. Addressing the data-scarcity and geographic bias of v1.0.3, v1.1.0 delivers a **$\sim 95\times$ scale-up in training data**, incorporates **three major US metropolitan areas**, implements **strict data quality control**, trains for a full **60 epochs on local RTX 4050 GPU**, and achieves dramatic accuracy improvements across all terrain and height strata.

| Benchmark Dimension | DepthWizard v1.0.3 | DepthWizard v1.1.0 | Improvement / Significance |
| :--- | :---: | :---: | :--- |
| **Training Dataset Size** | 40 crops (~10 tiles) | **3,817 crops (1,050 tiles)** | **$\sim 95\times$ Data Scale-Up** |
| **Geographic Diversity** | 1 city (Philadelphia biased) | **3 cities (DC, NYC, PHL)** | Multi-city cross-urban generalization |
| **Quality Control Filter** | Basic clip ($>0\text{m}$) | **Strict QC pipeline** | Dropped 544 defective tiles ($>30\%$ NaN, $<-1\text{m}$) |
| **Omaha / Jax Artifacts** | Unverified | **0 OMA / JAX instances** | Cleaned upstream noisy labels |
| **Test Set Overall RMSE** | `6.7508m` | **`4.4672m`** | **33.8% Error Reduction** |
| **Test Set Overall MAE** | `3.9340m` | **`2.3645m`** | **39.9% Error Reduction** |
| **Test Set Median AE** | `1.7133m` | **`0.7084m`** | **58.7% Error Reduction (Sub-metre!)** |
| **LE90 Linear Error** | `10.8202m` | **`6.8767m`** | **36.4% Error Reduction** |
| **Pearson Correlation ($r$)** | `0.5868` | **`0.8374`** | **Massive Correlation Surge (+0.2506)** |
| **$\delta < 2.5\text{m}$ Accuracy** | `58.60%` | **`69.60%`** | **+11.00 Percentage Points** |
| **Building RMSE (Class 3)** | `8.5270m` | **`5.4257m`** | **36.4% Error Reduction on Buildings** |
| **Tall Strata ($15-30\text{m}$)** | `13.5844m` | **`7.3037m`** | **46.2% Error Reduction on Tall Buildings** |

---

## 📦 What Was Built & Changed

### 1. Ingestion & Quality Control Engine (`scripts/prepare_gamus_v110.py`)
- Sourced from canonical Hugging Face dataset `earthflow/GAMUS`.
- Downloaded 1,500 complete tile triplets across 3 modalities (`images/`, `heights/`, `classes/`).
- Extracted four 518x518 crops per 1024x1024 tile (preserving native 0.33 m GSD and ViT-S/14 patch grid compatibility).
- Implemented automated rejection rules:
  - Dropped crops with $>30\%$ nodata / NaN pixels (134 events).
  - Quarantined crops with unphysical negative heights $<-1.0\text{m}$ (406 events).
  - Quarantined crops containing solely class 0 background (4 events).
- Produced verified manifest at `data/gamus/manifest.csv` with 5,456 total realized crops (3,817 train / 568 val / 1,071 test).

### 2. Numerical Stability & Training Infrastructure (`training/train_v110.py`)
- **FP32 Composite Loss**: Resolved logarithmic variance overflow under AMP `float16` by casting model predictions and targets to `fp32` before computing SILog loss, guaranteeing 100% finite gradients throughout training.
- **Stateful Resumption Engine**: Supported robust resume from `models/v1.1.0/last.pt`, exact cosine learning rate scheduler fast-forwarding, continuous history preservation in CSV/JSONL, and live curve plotting.
- **Dynamic Checkpoint Serialization**: Recorded `models/v1.1.0/best.pt` (best overall validation RMSE), `models/v1.1.0/best_tall.pt` (best tall structure RMSE $\ge 15\text{m}$), and real-time state in `models/v1.1.0/checkpoint_state.json`.

### 3. Rigorous Bitwise Weight Audit (`scripts/audit_weights_v110.py`)
- Bitwise compared `models/v1.1.0/best.pt` against foundational base `models/depth_anything_v2_vits.pth` and prior `models/dav2s_gamus_ft_v1.pth`.
- Verified that **100.0% of vision backbone weights (175/175 tensors) remained bitwise identical to official DINOv2 weights** (`max abs diff == 0.0`), preventing catastrophic forgetting.
- Verified that **93.8% of DPT decoder weights (60/64 tensors)** evolved under gradient descent.

### 4. Comprehensive Evaluation Suite (`scripts/evaluate_v110.py`)
- Evaluated 1,071 held-out test crops (35,139,491 valid reference pixels) across 4 candidate models:
  1. Base Zero-Shot (relative depth + per-crop affine least-squares fit)
  2. v1.0.3 Checkpoint
  3. v1.1.0 Best Validation Checkpoint (`best.pt`)
  4. v1.1.0 Best Tall Checkpoint (`best_tall.pt`)
- Exported complete metrics to `artifacts/v1.1.0/metrics_v1.1.0.json`.
- Rendered diagnostic CDF error curves, height-stratified RMSE bar charts, tall structure scatter plots, and exported GeoTIFF difference rasters to `artifacts/v1.1.0/rasters/`.

---

## 📊 Summary of Test Set Performance

### City-by-City Metrics
- **Washington DC**: RMSE dropped from `8.38m` $\to$ **`4.94m`**; correlation jumped from `0.625` $\to$ **`0.877`**.
- **New York City**: RMSE dropped from `7.20m` $\to$ **`4.97m`**; correlation jumped from `0.463` $\to$ **`0.787`**.
- **Philadelphia**: RMSE dropped from `4.46m` $\to$ **`3.54m`**; MAE dropped to **`1.56m`**; MedAE reached **`0.30m`** with **`79.81%`** of pixels within 2.5m.

### Land-Cover Class Metrics
- **Ground (Class 1)**: MAE **`0.55m`**, MedAE **`0.04m`**, 93.3% within 2.5m.
- **Buildings (Class 3)**: RMSE **`5.43m`** (down from 8.53m in v1.0.3), MAE **`3.23m`** (down from 5.20m).
- **Tree Canopy (Class 6)**: RMSE **`6.40m`** (down from 9.77m in v1.0.3), MAE **`4.75m`** (down from 7.58m).
- **Roads (Class 5)**: MAE **`1.24m`**, MedAE **`0.05m`**, 85.6% within 2.5m.

---

## 🛡️ Scope Fence Verification
Executed `scripts/verify_scope_fence.py`:
- Checked all 74 baseline repo files against `artifacts/v1.1.0/fence_hashes_before.json`.
- Result: **100% match (0 violations)**.
- All v1.1.0 code and outputs reside strictly in designated directories (`training/`, `scripts/`, `models/v1.1.0/`, `artifacts/v1.1.0/`, `docs/`).

---

## 🏁 Checkpoint Access
- Primary Release Checkpoint: `models/v1.1.0/best.pt`
- Tall-Structure Checkpoint: `models/v1.1.0/best_tall.pt`
- Training State Metadata: `models/v1.1.0/checkpoint_state.json`
- Quantitative Evaluation: `artifacts/v1.1.0/metrics_v1.1.0.json`
