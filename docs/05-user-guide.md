# 05 — DepthWizard User Guide

## Getting Started
DepthWizard provides an intuitive web platform to reconstruct 3D terrain and perform height analysis from optical satellite and aerial imagery.

### 1. Uploading Imagery
1. Navigate to the **Upload Page** (`http://localhost:8080` or `http://localhost:5173`).
2. Drag and drop your image file:
   - **GeoTIFF with CRS**: DepthWizard automatically routes through the georeferenced pipeline, fetches SRTM terrain anchors, and outputs absolute metric heights in metres (EGM96).
   - **Plain PNG / JPG / TIFF without CRS**: DepthWizard routes through the relative pipeline, generating a normalized relative elevation model.
3. For non-georeferenced images, optionally enter the estimated Ground Sample Distance (GSD in metres).
4. Click **Process Imagery**.

### 2. 3D Flythrough Navigation
Once processing completes, the platform transitions to the **3D Viewer**:
- **Orbit Mode (Default)**: Left-click and drag to rotate the terrain, right-click to pan, scroll to zoom.
- **First-Person Fly Mode**:
  - Click anywhere on the terrain to lock the pointer.
  - **W / A / S / D**: Move forward, left, backward, right.
  - **Q / E**: Descend / ascend vertically.
  - **Shift**: Accelerate / speed boost.
  - **Esc**: Exit first-person fly mode.
- **Top-Down (Nadir) Mode**: Orthographic top-down inspection to verify exact projection alignment against the raw optical image.

### 3. Height & Slope Analysis Tools
- **Height Probe**: Hover or click on any building, tree, or ground pixel to view its authoritative height in metres (or relative units) with vertical datum attribution.
- **Slope Tool**: Toggle the slope overlay to inspect terrain gradients in degrees computed via directional Sobel kernels.
- **Measurement Tool**: Click two points to measure Euclidean ground distance and elevation delta ($\Delta Z$).
- **Vertical Exaggeration**: Adjust the slider from $1.0\times$ to $5.0\times$ to accentuate subtle topological features.

### 4. Validation Page
1. Upload a reference LiDAR/DEM GeoTIFF.
2. View the synchronized split-screen comparison, signed-error heatmap (RdBu_r $\pm 15$ m), and automated error metrics table (RMSE, MAE, Pearson $r$, $\delta_{1.0}$, $\delta_{2.5}$).
