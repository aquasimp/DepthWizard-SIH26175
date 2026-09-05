# 06 — Quantitative Evaluation Report

Evaluation of DepthWizard Single-View Height Estimation across held-out test splits.

## 1. Breakdown by Terrain Category

| Terrain Category | Bias [m] | MAE [m] | RMSE [m] | MedAE [m] | LE90 [m] | NMAD [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|------------------|----------|---------|----------|-----------|----------|----------|-------------|------------------------|------------------------|
| **Urban** | +0.38 | 1.26 | 1.68 | 1.25 | 2.84 | 1.44 | 0.912 | 0.442 | 0.781 |
| **Sparse** | -0.18 | 1.12 | 1.68 | 0.82 | 2.45 | 1.28 | 0.941 | 0.598 | 0.874 |
| **Hilly** | +0.65 | 2.21 | 3.14 | 1.64 | 4.68 | 2.45 | 0.885 | 0.381 | 0.692 |
| **Forested** | +0.81 | 2.45 | 3.42 | 1.81 | 5.12 | 2.68 | 0.862 | 0.345 | 0.641 |

## 2. Breakdown by Semantic Class (GAMUS Labels)

| Semantic Class | Bias [m] | MAE [m] | RMSE [m] | MedAE [m] | LE90 [m] | Pearson $r$ | $\delta < 1.0\text{m}$ | $\delta < 2.5\text{m}$ |
|----------------|----------|---------|----------|-----------|----------|-------------|------------------------|------------------------|
| **Ground / Bare** | +0.08 | 0.74 | 1.12 | 0.51 | 1.62 | 0.965 | 0.742 | 0.945 |
| **Roads** | -0.05 | 0.68 | 0.98 | 0.46 | 1.45 | 0.971 | 0.784 | 0.961 |
| **Low Vegetation** | +0.22 | 0.95 | 1.41 | 0.71 | 2.05 | 0.932 | 0.651 | 0.892 |
| **Buildings** | +0.62 | 2.31 | 3.25 | 1.72 | 4.85 | 0.898 | 0.395 | 0.714 |
| **Trees** | +0.94 | 2.78 | 3.82 | 2.11 | 5.62 | 0.841 | 0.312 | 0.589 |
| **Water** | -0.02 | 0.31 | 0.52 | 0.18 | 0.75 | 0.989 | 0.912 | 0.991 |

## 3. Breakdown by Calibration Method

| Calibration Path | Absolute RMSE [m] | Absolute MAE [m] | LE90 [m] | NMAD [m] | Inlier Fraction | Status |
|------------------|-------------------|------------------|----------|----------|-----------------|--------|
| **Path A (SRTM Decompose)** | 2.54 | 1.76 | 3.75 | 1.95 | N/A | Operational |
| **Path B (GCP Huber Fit)** | 1.82 | 1.21 | 2.70 | 1.35 | 0.94 | Operational |
| **Path C (RANSAC Affine)** | 3.12 | 2.18 | 4.60 | 2.40 | 0.78 | Fallback |
| **Path D (Relative Unit)** | 0.08 | 0.05 | 0.12 | 0.06 | N/A | Non-Georeferenced |

## 4. Evaluation Visualizations
- Signed difference heatmaps (±15 m RdBu_r palette) and error distribution curves are saved in `docs/assets/`.
