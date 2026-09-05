# 03 — Scale Calibration Mathematical Foundations

DepthWizard implements four explicit calibration paths (Paths A through D) to anchor or normalize predicted heights.

---

## Path A: SRTM DTM Decomposition (Default Georeferenced)
When an input image possesses georeferencing metadata (CRS + Affine Transform) and SRTM coverage is available:

1. **Reprojection & Fetch**: Scene bounding box is transformed to EPSG:4326 to query SRTM GL1 (30 m).
2. **Resampling**: The fetched SRTM DEM is reprojected and resampled to the 0.33 m target raster grid via cubic spline interpolation:
   $$DEM_{\mathrm{SRTM}}(r, c)$$
3. **Low-Frequency Terrain Decomposition**:
   We extract the smooth ground topology by applying a morphological opening with structuring element diameter $\approx 90\text{ m}$, followed by Gaussian filtering ($\sigma \approx 60\text{ m}$):
   $$DTM_{\mathrm{smooth}} = \mathcal{G}_{\sigma} \left( \mathcal{M}_{90}(DEM_{\mathrm{SRTM}}) \right)$$
4. **Surface Model Composition**:
   Because the fine-tuned head outputs metric nDSM (height above ground level in metres), absolute elevation is recovered by:
   $$DSM(r, c) = DTM_{\mathrm{smooth}}(r, c) + \max\left(0, nDSM(r, c)\right)$$
5. **Vertical Datum**: Assigned to **EGM96** (orthometric height in metres).

---

## Path B: Ground Control Point (GCP) Residual Field Fitting
When $N$ sparse GCPs $(x_i, y_i, Z_i)$ are supplied by the user:

1. Let $r_i = Z_i - DSM_{\mathrm{PathA}}(x_i, y_i)$ be the residual elevation error at each GCP.
2. Define normalized scene coordinates $(x_h, y_h) \in [-1, 1]^2$.
3. We fit a parametric correction surface:
   $$\delta Z(x_h, y_h) = c_0 + c_1 x_h + c_2 y_h + c_3 x_h y_h + c_4 x_h^2 + c_5 y_h^2$$
4. **Adaptive Degeneracy Rule**: To prevent overfitting, the model order is constrained by $N$:
   - $N < 4$: Constant offset only ($c_0$)
   - $4 \le N < 8$: Planar surface ($c_0 + c_1 x_h + c_2 y_h$)
   - $N \ge 8$: Full quadratic surface ($c_0 \dots c_5$)
   - Invariant: Never fit more parameters than $N / 2$.
5. **Solver**: Solved using Huber iteratively reweighted least squares (IRLS) via `scipy.optimize.least_squares(loss='huber', f_scale=2.0)`.

---

## Path C: RANSAC Affine Disparity Alignment (Fallback / Zero-Shot)
For zero-shot models predicting disparity $d(x, y)$ (where higher disparity = closer to sensor = higher elevation):

1. **Pseudo-Ground Mask**: In local $200 \times 200$ px windows, select pixels below the 15th percentile of $d$. Morphologically clean with opening to isolate terrain and avoid rooftops.
2. **Sampling**: Sample $M \approx 5000$ points and extract paired $(d_j, Z_{\mathrm{SRTM}, j})$.
3. **Robust Estimation**:
   Fit $Z = a \cdot d + b$ using `RANSACRegressor(residual_threshold=8.0, max_trials=1000)`.
   Refit inliers with `HuberRegressor` and `TheilSenRegressor`, selecting the model with minimal inlier MAE.
4. **Degeneracy Guard (Mandatory)**:
   If $\mathrm{std}(Z_{\mathrm{SRTM}}) < 5.0\text{ m}$ (flat terrain):
   - Slope $a$ is mathematically unidentifiable from noisy SRTM.
   - Set `calibration_status = "DEGENERATE_FLAT_TERRAIN"`.
   - Scale $a$ such that the 99.5th percentile of $nDSM$ equals `assumed_max_structure_height_m` (default 45.0 m).
   - $b = \mathrm{median}(Z_{\mathrm{SRTM}})$.

---

## Path D: Relative Disparity Normalization (Non-Georeferenced)
For images lacking CRS (plain PNG/JPG or unreferenced TIFFs):

1. Compute 1st percentile $p_1$ and 99th percentile $p_{99}$ over valid pixels.
2. Compute normalized relative height:
   $$rDSM(r, c) = \operatorname{clip}\left( \frac{d(r, c) - p_1}{p_{99} - p_1}, 0.0, 1.0 \right)$$
3. Flag metadata:
   `is_absolute = false`, `units = "relative"`, `calibration_status = "RELATIVE_ONLY"`.
4. If the user provides a reference object height and GSD, map linearly and flag as `"PSEUDO_METRIC"`.
