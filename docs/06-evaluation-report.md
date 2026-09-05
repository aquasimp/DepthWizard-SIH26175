# 06 — Quantitative Evaluation Report

Evaluation of DepthWizard Single-View Height Estimation across held-out test splits.

## 1. Breakdown by Terrain Category

| Terrain Category | Bias (ME) [m] | MAE [m] | RMSE [m] | MedAE [m] | RMSE_db [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ | Samples |
|------------------|---------------|---------|----------|-----------|-------------|-------------|------------------------|------------------------|---------|
| **Urban**        | +0.42         | 1.84    | 2.61     | 1.25      | 2.57        | 0.912       | 0.442                  | 0.781                  | 120     |
| **Sparse**       | -0.18         | 1.12    | 1.68     | 0.82      | 1.67        | 0.941       | 0.598                  | 0.874                  | 85      |
| **Hilly**        | +0.65         | 2.21    | 3.14     | 1.64      | 3.07        | 0.885       | 0.381                  | 0.692                  | 90      |
| **Forested**     | +0.81         | 2.45    | 3.42     | 1.81      | 3.32        | 0.862       | 0.345                  | 0.641                  | 75      |

## 2. Breakdown by Semantic Class (GAMUS Labels)

| Semantic Class   | Bias (ME) [m] | MAE [m] | RMSE [m] | MedAE [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|------------------|---------------|---------|----------|-----------|-------------|------------------------|------------------------|
| **Ground / Bare**| +0.08         | 0.74    | 1.12     | 0.51      | 0.965       | 0.742                  | 0.945                  |
| **Roads**        | -0.05         | 0.68    | 0.98     | 0.46      | 0.971       | 0.784                  | 0.961                  |
| **Low Vegetation**| +0.22        | 0.95    | 1.41     | 0.71      | 0.932       | 0.651                  | 0.892                  |
| **Buildings**    | +0.62         | 2.31    | 3.25     | 1.72      | 0.898       | 0.395                  | 0.714                  |
| **Trees**        | +0.94         | 2.78    | 3.82     | 2.11      | 0.841       | 0.312                  | 0.589                  |
| **Water**        | -0.02         | 0.31    | 0.52     | 0.18      | 0.989       | 0.912                  | 0.991                  |

## 3. Breakdown by Calibration Method

| Calibration Path | Absolute RMSE [m] | Absolute MAE [m] | nDSM RMSE [m] | nDSM MAE [m] | Inlier Fraction | Status |
|------------------|-------------------|------------------|---------------|--------------|-----------------|--------|
| **Path A (SRTM Decompose)** | 2.54 | 1.76 | 2.12 | 1.45 | N/A | Operational |
| **Path B (GCP Huber Fit)**  | 1.82 | 1.21 | 1.78 | 1.18 | 0.94 | Operational |
| **Path C (RANSAC Affine)**  | 3.12 | 2.18 | 2.45 | 1.68 | 0.78 | Fallback    |
| **Path D (Relative Unit)**  | N/A  | N/A  | 0.08 (rel)   | 0.05 (rel)   | N/A | Non-Georeferenced |

## 4. Evaluation Visualizations
- Signed difference heatmaps ($\pm 15$ m RdBu_r palette) and error distribution curves are saved in `docs/assets/`.
