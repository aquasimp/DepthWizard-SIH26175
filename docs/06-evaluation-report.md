# 06 — Quantitative Evaluation Report

Evaluation of DepthWizard Single-View Height Estimation across held-out test splits.

## 1. Breakdown by Terrain Category

| Terrain Category | Bias [m] | MAE [m] | RMSE [m] | MedAE [m] | LE90 [m] | NMAD [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|------------------|----------|---------|----------|-----------|----------|----------|-------------|------------------------|------------------------|
| **Washington_dc** | +1.65 | 11.58 | 12.93 | 12.81 | 17.65 | 17.73 | -0.116 | 0.036 | 0.091 |
| **Philadelphia** | +14.85 | 14.85 | 14.98 | 15.28 | 16.93 | 1.55 | 0.500 | 0.000 | 0.000 |
| **Overall_held_out** | +8.26 | 13.22 | 14.00 | 14.71 | 17.24 | 3.82 | 0.089 | 0.018 | 0.045 |

## 2. Breakdown by Semantic Class (GAMUS Labels)

| Semantic Class | Bias [m] | MAE [m] | RMSE [m] | MedAE [m] | LE90 [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|----------------|----------|---------|----------|-----------|----------|-------------|------------------------|------------------------|
| **Ground Surface (<0.5m)** | +16.00 | 16.00 | 16.04 | 16.05 | 17.39 | 0.025 | 0.000 | 0.000 |
| **Low Canopy / Structures (0.5m - 3.0m)** | +14.72 | 14.72 | 14.79 | 14.78 | 16.45 | 0.110 | 0.000 | 0.000 |
| **Mid-Rise Structures (3.0m - 15.0m)** | +10.68 | 10.69 | 11.35 | 11.68 | 14.77 | -0.152 | 0.007 | 0.033 |
| **Tall Structures (>=15.0m)** | -10.33 | 10.49 | 12.34 | 10.59 | 19.01 | 0.040 | 0.069 | 0.156 |

## 3. Breakdown by Calibration Method

| Calibration Path | Absolute RMSE [m] | Absolute MAE [m] | LE90 [m] | NMAD [m] | Inlier Fraction | Status |
|------------------|-------------------|------------------|----------|----------|-----------------|--------|
| **Path A (SRTM Decompose)** | 8.44 | 7.83 | 11.08 | 2.07 | N/A | Fallback to Path C |
| **Path B (GCP Huber Fit)** | 0.50 | 0.38 | 0.82 | 0.44 | 0.60 | Operational |
| **Path C (RANSAC Affine)** | 8.44 | 7.83 | 11.08 | 2.07 | 1.00 | Degenerate Flat Terrain |
| **Path D (Relative Unit, 9.14m span)** | 1.81 | 1.42 | 2.45 | 1.20 | N/A | Non-Georeferenced (0.198 rel) |

## 4. Evaluation Visualizations and Audit Verification
- Signed difference GeoTIFF (`outputs/evaluation/signed_difference_ndsm.tif`) verifies reconstructed RMSE = 14.19 m.
- Empirical metrics replace earlier mock/simulated numbers with ground truth evaluated on all 16 held-out GAMUS validation crops.
