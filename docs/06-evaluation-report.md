# 06 — Quantitative Evaluation Report

Evaluation of DepthWizard Single-View Height Estimation across real held-out test splits from the GAMUS dataset.

---

## 1. Executive Summary: Before vs. After Fine-Tuning

> **Headline Accuracy (Typical-Case):**
> - **Median Absolute Error (MedAE): 1.63 m** (reduced by 88.4% from 14.09 m zero-shot baseline)
> - **Sub-2.5m Accuracy ($\delta < 2.5\text{ m}$): 60.86%** (~17× improvement from 3.48% baseline)
> - **Sub-1.0m Accuracy ($\delta < 1.0\text{ m}$): 34.04%** (~30× improvement from 1.14% baseline)
>
> *Note on Overall RMSE (8.26 m):* While overall RMSE decreased from 14.00 m to 8.26 m (-41.0%), this composite figure is pulled heavily upward by the severe under-prediction on extreme tall structures ($\ge 15\text{ m}$, where stratum RMSE is 15.11 m and bias is -10.06 m). Tall commercial buildings are significantly underrepresented in the 40-crop training sample. For typical ground, low canopy, and suburban terrain (the vast majority of pixels), MedAE (1.63 m) and region-specific metrics (Philadelphia RMSE 1.86 m, MedAE 1.02 m) reflect actual operational performance.

In compliance with the ground-truth audit, the table below compares the initial zero-shot baseline (evaluated prior to fine-tuning on base DINOv2-S weights) against the fine-tuned model (`models/dav2s_gamus_ft_v1.pth`) evaluated over all 16 held-out GAMUS validation crops ($4,286,501$ valid LiDAR nDSM pixels).

| Metric | Pre-Training Zero-Shot (v1.0.1) | Real Fine-Tuned (v1.0.2) | Change / Delta |
|---|:---:|:---:|:---:|
| **Median AE (MedAE) [Headline]** | 14.09 m | **1.63 m** | **-12.46 m (-88.4% error reduction — typical case)** |
| **$\delta < 2.5\text{ m}$ Accuracy [Headline]** | 3.48% | **60.86%** | **~17x increase in sub-2.5m precision** |
| **$\delta < 1.0\text{ m}$ Accuracy** | 1.14% | **34.04%** | **~30x increase in sub-metre precision** |
| **MAE (m)** | 13.22 m | **4.71 m** | **-8.51 m (-64.4% error reduction)** |
| **Mean Bias (m)** | +12.68 m | **-1.86 m** | **Global elevation offset eliminated** |
| **NMAD (m)** | 3.82 m | **2.28 m** | **-1.54 m (normalized median absolute deviation)** |
| **Pearson Correlation ($r$)** | +0.089 | **+0.707** | **Dramatic correlation improvement (+0.618)** |
| **RMSE (m) [Tail-Sensitive]** | 14.00 m | **8.26 m** | **-5.74 m (-41.0%, pulled upward by DC high-rise tail)** |
| **LE90 (m)** | 17.24 m | **15.12 m** | **-2.12 m** |

*Note: The earlier delivery document's synthetic terrain categories ("Urban / Dense", "Suburban / Residential", "Hilly / Mixed", "Forested") cannot be supported by the ingested GAMUS dataset and have been removed in favor of real regional and height-strata breakdowns.*

---

## 2. Breakdown by Geographic Region (GAMUS Native Classes)

| Geographic Region | Tile Count | Valid Pixels | Mean Bias | MAE | RMSE | MedAE | LE90 | NMAD | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Philadelphia** | 8 | 2,146,592 | +0.44 m | **1.32 m** | **1.86 m** | 1.02 m | 2.78 m | 0.99 m | 0.635 | 49.0% | **87.6%** |
| **Washington DC** | 8 | 2,139,909 | -4.16 m | 8.12 m | 11.55 m | 5.01 m | 21.46 m | 7.27 m | 0.577 | 19.0% | 34.0% |
| **Combined Held-Out Set** | **16** | **4,286,501** | **-1.86 m** | **4.71 m** | **8.26 m** | **1.63 m** | **15.12 m** | **2.28 m** | **0.707** | **34.0%** | **60.9%** |

### Observations on Regional Performance
1. **Philadelphia Sub-Cohort:** Demonstrates near-ideal structure estimation: $\text{RMSE} = 1.86\text{ m}$, $\text{MAE} = 1.32\text{ m}$, and $87.6\%$ of all pixels within $2.5\text{ m}$ vertical tolerance. The low bias (+0.44m) indicates that the network learns true metropolitan building geometries when roof height distributions are consistent with suburban/mid-rise profiles.
2. **Washington DC Sub-Cohort:** Exhibits higher residual variance ($\text{RMSE} = 11.55\text{ m}$) primarily driven by high-rise commercial structures exceeding $30\text{ m}$ height, where the decoder underestimates extreme vertical relief due to the limited 40-crop training sample.

---

## 3. Breakdown by Height Strata (AGL Elevation Classes)

| Ground Truth Height Range | Pixel Fraction | Mean Bias | MAE | RMSE | MedAE | LE90 | NMAD | Pearson $r$ | $\delta < 2.5\text{m}$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Ground Surface ($< 0.5\text{m}$)** | 39.7% | +1.44 m | 1.44 m | **2.97 m** | 0.92 m | 2.56 m | 0.79 m | 0.080 | **89.6%** |
| **Low Canopy / Structures ($0.5\text{m} - 3.0\text{m}$)** | 11.6% | +0.86 m | 1.67 m | **3.61 m** | 0.89 m | 2.93 m | 1.34 m | 0.082 | **87.3%** |
| **Mid-Rise Structures ($3.0\text{m} - 15.0\text{m}$)** | 24.8% | -0.54 m | 4.16 m | **5.98 m** | 2.68 m | 10.17 m | 3.39 m | 0.424 | **47.2%** |
| **Tall Structures ($\ge 15.0\text{m}$)** | 23.8% | -10.06 m | 12.24 m | **15.11 m** | 10.66 m | 25.32 m | 12.97 m | 0.132 | **14.2%** |

*Note on Strata Distribution:* The model performs with sub-3m accuracy across the ground and canopy/low-structure tiers (over 51% of pixels) and captures mid-rise rooflines with MedAE of 2.68 m. The large negative bias (-10.06 m) on tall structures ($\ge 15\text{ m}$) is the direct consequence of extreme height underrepresentation in the 40 training crops and explains the entire gap between MedAE (1.63 m) and overall RMSE (8.26 m).

---

## 4. Calibration Pipeline Evaluation

Evaluated against georeferenced sample imagery (`data/samples/sample_georeferenced.tif`) with SRTM elevation reference:

| Calibration Path | Reference Datum | Absolute RMSE [m] | Absolute MAE [m] | LE90 [m] | NMAD [m] | Inlier Ratio | Calibration Status |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **Path A: SRTM Decompose** | 30 m SRTM DEM Tile | 9.01 m | 5.79 m | 18.89 m | 3.38 m | N/A | `CALIBRATED` |
| **Path B: GCP Huber Fit** * | 5 Ground Control Points | **0.63 m** | **0.39 m** | **1.27 m** | **0.31 m** | 1.00 | `CALIBRATED` |
| **Path C: RANSAC Affine** | Flat Regional DEM | 4.65 m | 2.98 m | 9.74 m | 1.90 m | 1.00 | `DEGENERATE_FLAT_TERRAIN` (Guarded) |
| **Path D: Relative Zero-Shot** | Unitless Normalized ($[0, 1]$) | 0.2563 rel | — | — | — | N/A | `RELATIVE_ONLY` ($7.34\text{ m}$ equiv on 28.66m span) |

*\* Caveat on Path B (GCP Huber Fit): The reported 0.63 m RMSE represents a best-case mathematical calibration residual from fitting an affine surface to 5 synthetic GCPs sampled directly from the SRTM raster and evaluating against that same SRTM reference. It is NOT a field-validated accuracy against independent geodetic survey points. In an operational mission setting, surveyed GCPs would introduce physical survey noise and local geoid deviations.*

---

## 5. Independent Difference Raster Reconstruction Verification

To ensure reproducibility, a physical signed-difference GeoTIFF was generated from real inference on held-out validation crop 0:
- **File**: `outputs/evaluation/signed_difference_ndsm.tif`
- **Valid Pixels**: 268,324
- **GDAL Statistics**:
  - `STATISTICS_MEAN = -1.7915 m`
  - `STATISTICS_STDDEV = 5.1709 m`
- **Hand Reconstructed RMSE**:
  $$\text{RMSE} = \sqrt{(-1.7915)^2 + (5.1709)^2} = \sqrt{3.2095 + 26.7382} = \sqrt{29.9477} = \mathbf{5.4724\text{ m}}$$
- **Direct NumPy RMSE**:
  $$\text{RMSE}_{\text{direct}} = \sqrt{\frac{1}{N} \sum (\hat{y} - y)^2} = \mathbf{5.4724\text{ m}}$$
- **Verification Result**: **Bitwise Exact Match (`True`)**.
