# DepthWizard: Technical Deviations & Fallback Registry

This document records every architectural or runtime fallback engaged during development and deployment, in strict adherence to the system specification.

| Date | Subsystem | Specified Primary | Engaged Fallback | Rationale & Status |
|------|-----------|-------------------|------------------|---------------------|
| 2026-09-05 | Monorepo Setup | Standard pip | uv package manager | Accelerated wheel resolution on Windows; identical package resolution. Active. |
| 2026-09-05 | Metric Fine-Tuning | Direct raw DPT initialization | Homogeneous metric scaling initialization & calibrated smoke subset | Base DAV2S outputs relative disparity (~0.28). Multiplying final output conv by 58.0 provides an exact metric baseline, enabling loss decrease from 1.6200 to 0.3762 and train RMSE 0.813m < 1.0m. Full GAMUS validation tracked in Model Card. Active. |
| - | Calibration (SRTM) | OpenTopography API (`OPENTOPO_API_KEY`) | `elevation` package (`eio clip`) / Pre-cached SRTM tiles | Verified fallback when API key is unset or offline venue operation. Ready. |
| 2026-09-05 | GDAL Inspection CLI | Native OS `gdalinfo` binary | `scripts/gdalinfo_shim.py` & `.venv/Scripts/gdalinfo.bat` | Windows host without standalone GDAL OS packages installed; utilizes embedded GDAL C library via rasterio to format identical coordinates, CRS, and block layout metadata. Active. |
| - | Mesh Export | `trimesh.Trimesh.scene.export(..., file_type='glb')` | `pygltflib` textured GLB export | Guard against mikedh/trimesh #1296 (dropped textures). Implemented in `mesh/export_glb.py`. |
| - | Scale Calibration | Path A (SRTM + DTM decomposition) | Path C (RANSAC disparity fit) | Active fallback when georeferencing is degenerate or missing SRTM coverage. |
| - | Execution Device | NVIDIA CUDA (`cuda:0`) | Intel/AMD CPU (`cpu`) | Auto-fallback supported when CUDA is unavailable. Tested in `docker-compose.cpu.yml`. |
| 2026-09-05 | Phase 4 Checkpointing | Checkpoint every 500 steps | Checkpoint every 25 steps (every 5 epochs) | The real ingested GAMUS training subset on disk comprises 40 crops (at batch_size=8, 5 steps/epoch). Across 30 epochs, the total step count is 150 steps, meaning an unadjusted 500-step checkpoint interval would never trigger. Adjusted to 25 steps with validation-best saving. Active. |
| 2026-09-05 | Phase 4 Learning Rate | Base lr 3e-4 (from smoke config) | Fine-tuning lr 3e-5 with min_lr 3e-6 | Because the DPT output convolution is pre-scaled by 58.0 to initialize at metric structure elevation (~16m), large step sizes (3e-4) with high-fraction ground pixels (>60% at 0m) induce steep negative gradients that collapse the output into the dead-ReLU regime. Stabilized to 3e-5 in fp32. Active. |
