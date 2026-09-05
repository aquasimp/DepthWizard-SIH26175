# DepthWizard: Technical Deviations & Fallback Registry

This document records every architectural or runtime fallback engaged during development and deployment, in strict adherence to the system specification.

| Date | Subsystem | Specified Primary | Engaged Fallback | Rationale & Status |
|------|-----------|-------------------|------------------|---------------------|
| 2026-09-05 | Monorepo Setup | Standard pip | uv package manager | Accelerated wheel resolution on Windows; identical package resolution. Active. |
| - | Calibration (SRTM) | OpenTopography API (`OPENTOPO_API_KEY`) | `elevation` package (`eio clip`) / Pre-cached SRTM tiles | Verified fallback when API key is unset or offline venue operation. Ready. |
| - | Mesh Export | `trimesh.Trimesh.scene.export(..., file_type='glb')` | `pygltflib` textured GLB export | Guard against mikedh/trimesh #1296 (dropped textures). Implemented in `mesh/export_glb.py`. |
| - | Scale Calibration | Path A (SRTM + DTM decomposition) | Path C (RANSAC disparity fit) | Active fallback when georeferencing is degenerate or missing SRTM coverage. |
| - | Execution Device | NVIDIA CUDA (`cuda:0`) | Intel/AMD CPU (`cpu`) | Auto-fallback supported when CUDA is unavailable. Tested in `docker-compose.cpu.yml`. |
