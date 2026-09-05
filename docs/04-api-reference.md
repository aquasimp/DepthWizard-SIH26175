# 04 — REST API Reference

The DepthWizard backend exposes a REST API via FastAPI on port 8000. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

---

## Endpoint Specifications & Curl Examples

### 1. Upload Imagery & Create Job
- **Route**: `POST /api/jobs`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Imagery file (GeoTIFF, TIFF, PNG, JPG). Max dimensions $8000 \times 8000$ px.
  - `assumed_gsd_m` (optional float, default 0.33): Assumed GSD for unreferenced images.
  - `calibration_path` (optional string): Force specific calibration path (`"PATH_A"`, `"PATH_B"`, `"PATH_C"`, `"PATH_D"`).
  - `z_exag` (optional float, default 1.0): Vertical exaggeration factor for 3D meshes.
- **Example Curl**:
  ```bash
  curl -X POST "http://localhost:8000/api/jobs" \
    -F "file=@data/samples/sample_georeferenced.tif" \
    -F "assumed_gsd_m=0.33" \
    -F "z_exag=1.0"
  ```
- **Response** (`201 Created`):
  ```json
  {
    "job_id": "job_1725539400_a1b2c3d4",
    "status": "PENDING",
    "message": "Job created and queued for processing."
  }
  ```
- **Error Response** (`422 Unprocessable Entity`):
  ```json
  {
    "detail": {
      "error_code": "CORRUPT_IMAGE",
      "detail": "Failed to read image: Unrecognized header format"
    }
  }
  ```

---

### 2. Poll Job Status
- **Route**: `GET /api/jobs/{job_id}`
- **Example Curl**:
  ```bash
  curl -X GET "http://localhost:8000/api/jobs/job_1725539400_a1b2c3d4"
  ```
- **Response** (`200 OK`):
  ```json
  {
    "job_id": "job_1725539400_a1b2c3d4",
    "status": "PROCESSING",
    "stage": "INFER",
    "progress": 60,
    "error": null,
    "created_at": "2026-09-05T12:00:00.000Z",
    "updated_at": "2026-09-05T12:00:05.120Z",
    "metadata": {
      "is_georeferenced": true,
      "gsd_m": 0.33,
      "width": 512,
      "height": 512,
      "infer_time_seconds": 0.42
    }
  }
  ```

---

### 3. Retrieve Generated Artifacts
- **Route**: `GET /api/jobs/{job_id}/artifacts/{name}`
- **Artifact Names**:
  - `dsm.tif`: Absolute GeoTIFF DSM (georeferenced jobs, EGM96 datum, float32, tiled LZW).
  - `ndsm.tif`: Normalized above-ground height GeoTIFF (bias-free metric layer).
  - `rdsm.tif`: Relative DSM GeoTIFF (unreferenced consumer images).
  - `heightmap_16bit.png`: 16-bit quantized heightmap for WebGL/Three.js renderer.
  - `heightmap.meta.json`: Sidecar JSON recording linear decoding formula and range.
  - `texture.jpg`: Power-of-two RGB texture (JPEG quality 90).
  - `terrain_lod0.glb`: Full resolution 3D mesh ($512 \times 512$, $<400\text{k}$ vertices).
  - `terrain_lod1.glb`: Medium resolution 3D mesh ($256 \times 256$).
  - `terrain_lod2.glb`: Low resolution 3D mesh ($128 \times 128$).
- **Example Curl**:
  ```bash
  curl -O "http://localhost:8000/api/jobs/job_1725539400_a1b2c3d4/artifacts/terrain_lod0.glb"
  ```

---

### 4. Upload Reference DSM & Trigger Evaluation
- **Route**: `POST /api/jobs/{job_id}/reference`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Ground truth or LiDAR DSM GeoTIFF.
- **Example Curl**:
  ```bash
  curl -X POST "http://localhost:8000/api/jobs/job_1725539400_a1b2c3d4/reference" \
    -F "file=@reference_lidar_dsm.tif"
  ```
- **Response** (`200 OK`):
  ```json
  {
    "job_id": "job_1725539400_a1b2c3d4",
    "status": "EVALUATED",
    "metrics_absolute": {
      "bias": -0.12,
      "mae": 0.84,
      "rmse": 1.15,
      "medae": 0.65,
      "rmse_db": 1.14,
      "pearson_r": 0.94,
      "delta1": 0.82,
      "delta2_5": 0.95,
      "valid_pixels": 262144
    },
    "terrain_tag": "urban_dense"
  }
  ```

---

### 5. Get Cached Evaluation Metrics
- **Route**: `GET /api/jobs/{job_id}/metrics`
- **Example Curl**:
  ```bash
  curl -X GET "http://localhost:8000/api/jobs/job_1725539400_a1b2c3d4/metrics"
  ```

---

### 6. Submit GCPs for Path B Recalibration
- **Route**: `POST /api/jobs/{job_id}/gcps`
- **Content-Type**: `application/json`
- **Payload**:
  ```json
  {
    "gcps": [
      {"x": 323520.0, "y": 4307480.0, "z_true": 142.5},
      {"x": 323600.0, "y": 4307400.0, "z_true": 155.0},
      {"x": 323650.0, "y": 4307350.0, "z_true": 138.2}
    ]
  }
  ```
- **Example Curl**:
  ```bash
  curl -X POST "http://localhost:8000/api/jobs/job_1725539400_a1b2c3d4/gcps" \
    -H "Content-Type: application/json" \
    -d '{"gcps": [{"x": 323520.0, "y": 4307480.0, "z_true": 142.5}, {"x": 323600.0, "y": 4307400.0, "z_true": 155.0}, {"x": 323650.0, "y": 4307350.0, "z_true": 138.2}]}'
  ```

---

### 7. Health Check
- **Route**: `GET /api/health`
- **Example Curl**:
  ```bash
  curl -X GET "http://localhost:8000/api/health"
  ```
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "model_version": "1.0.0",
    "device": "cuda",
    "cuda_available": true
  }
  ```
