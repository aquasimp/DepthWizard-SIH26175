# 04 — REST API Reference

The DepthWizard backend exposes a REST API via FastAPI on port 8000.

## Endpoints

### 1. Upload Imagery & Create Job
- **Route**: `POST /api/jobs`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Imagery file (GeoTIFF, TIFF, PNG, JPG). Max dimensions $8000 \times 8000$ px.
  - `assumed_gsd_m` (optional float, default 0.33): User-assumed GSD for non-georeferenced images.
  - `calibration_mode` (optional string): `"auto"`, `"path_a"`, `"path_c"`, or `"path_d"`.
- **Response**:
  ```json
  {
    "job_id": "job_20260905_123456_abcd",
    "status": "PENDING",
    "message": "Job registered and queued for processing"
  }
  ```

### 2. Poll Job Status
- **Route**: `GET /api/jobs/{id}`
- **Response**:
  ```json
  {
    "job_id": "job_20260905_123456_abcd",
    "status": "INFER",
    "stage": "Running tiled depth inference",
    "progress": 45,
    "error": null,
    "metadata": {
      "is_georeferenced": true,
      "original_gsd": 0.30,
      "resample_factor": 1.10
    }
  }
  ```

### 3. Retrieve Generated Artifacts
- **Route**: `GET /api/jobs/{id}/artifacts/{name}`
- **Standard Artifact Names**:
  - `meta.json`: Full job metadata, calibration status, CRS, and formulas.
  - `dsm.tif`: Absolute GeoTIFF DSM (georeferenced jobs).
  - `ndsm.tif`: Metric nDSM GeoTIFF (above-ground height).
  - `heightmap_16bit.png`: 16-bit quantized heightmap.
  - `heightmap.meta.json`: 16-bit linear decoding formula and range.
  - `texture.jpg`: Power-of-two RGB texture.
  - `terrain_lod0.glb`: Primary 3D mesh ($512 \times 512$).
  - `terrain_lod1.glb`: Medium LOD ($256 \times 256$).
  - `terrain_lod2.glb`: Low LOD ($128 \times 128$).

### 4. Upload Reference DSM & Evaluate Metrics
- **Route**: `POST /api/jobs/{id}/reference`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Ground truth / LiDAR DSM GeoTIFF.
- **Response**: Triggers validation and returns metrics summary.

### 5. Get Evaluation Metrics
- **Route**: `GET /api/jobs/{id}/metrics`
- **Response**: JSON payload containing Bias, MAE, RMSE, MedAE, Pearson r, delta1, delta2_5, and semantic class breakdown.

### 6. Submit GCPs for Path B Recalibration
- **Route**: `POST /api/jobs/{id}/gcps`
- **Payload**:
  ```json
  {
    "gcps": [
      {"x": 500200.0, "y": 4200100.0, "z_true": 142.5},
      {"x": 500800.0, "y": 4200900.0, "z_true": 165.2}
    ]
  }
  ```

### 7. Health Check
- **Route**: `GET /api/health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "model_version": "1.0.0",
    "device": "cuda",
    "cuda_available": true
  }
  ```
