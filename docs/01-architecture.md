# 01 — System Architecture

```
                                  +---------------------------------------+
                                  | Single-View Optical RGB Remote Sensing|
                                  |       (GeoTIFF / TIFF / PNG / JPG)    |
                                  +---------------------------------------+
                                                      |
                                                      v
                                        +----------------------------+
                                        |  Input Georef Detection   |
                                        |       (io/detect.py)       |
                                        +----------------------------+
                                           /                       \
                      Georeferenced (GeoTIFF)                     Non-Georeferenced (PNG/JPG)
                                         /                           \
                                        v                             v
                        +-------------------------------+   +-----------------------------+
                        |  GSD Normalization -> 0.33m  |   |  Assumed GSD Normalization  |
                        +-------------------------------+   +-----------------------------+
                                        \                             /
                                         \                           /
                                          v                         v
                                    +-------------------------------------+
                                    | Seamless Tiling & Inference Engine  |
                                    |  - Depth Anything V3 Small (ViT-S)  |
                                    |  - Overlap Cosine-Feathered Blend   |
                                    |  - Overlap Region Median Matching   |
                                    +-------------------------------------+
                                                       |
                                                       v
                                    +-------------------------------------+
                                    |   Scale Calibration Decision Logic  |
                                    |  - Path A: SRTM 30m DTM Decompose   |
                                    |  - Path B: GCP Quadratic Huber Fit  |
                                    |  - Path C: RANSAC Affine + Guard    |
                                    |  - Path D: Relative [0, 1] Stretched|
                                    +-------------------------------------+
                                           /                       \
                                          v                         v
                           +----------------------------+  +-------------------------------+
                           |     Geospatial Writers     |  |       3D Mesh Generation      |
                           | - Absolute DSM (GeoTIFF)   |  | - Heightmap to Y-UP Mesh      |
                           | - Metric nDSM (GeoTIFF)    |  | - Identity UV Texturing       |
                           | - 16-bit Heightmap PNG     |  | - Decimated LODs (LOD0..LOD2) |
                           | - Sidecar meta.json        |  | - Textured Binary GLB Export  |
                           +----------------------------+  +-------------------------------+
                                                       \   /
                                                        v v
                                      +------------------------------------+
                                      | Interactive Web 3D Flythrough UI   |
                                      | - Three.js PBR Displaced Terrain   |
                                      | - First-Person Fly Controls (WASD) |
                                      | - Height Probe & Slope Tool        |
                                      | - Reference Validation & Heatmaps  |
                                      +------------------------------------+
```

## Architectural Invariants
1. **Identity Map in UV Space**:
   $$u = \frac{c}{C-1}, \quad v = \frac{r}{R-1}$$
   Because the DSM raster and the RGB texture share the exact same pixel grid, texture projection is analytically exact without camera matrix solving.
2. **Canonical 0.33 m/px GSD Normalization**:
   All inputs are resampled to 0.33 m/px before passing through the network, matching the fine-tuned GAMUS coordinate space.
3. **State Persistence**:
   All jobs maintain persistent on-disk state machines via `meta.json`.
