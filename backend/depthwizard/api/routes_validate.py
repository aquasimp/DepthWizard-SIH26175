"""API routes for reference DSM validation and GCP recalibration."""

import json

import numpy as np
import rasterio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from depthwizard.api.routes_jobs import get_job_manager
from depthwizard.api.schemas import GcpPayload, JobStatusResponse, MetricsResponse
from depthwizard.calibration.gcp_fit import calibrate_path_b
from depthwizard.eval.metrics import compute_elevation_metrics
from depthwizard.io.writers import export_job_rasters
from depthwizard.jobs.manager import JobManager
from depthwizard.mesh.export_glb import export_all_lod_glbs

router = APIRouter(prefix="/api/jobs", tags=["validation"])


@router.post("/{job_id}/reference", response_model=MetricsResponse)
async def upload_reference_dsm(
    job_id: str,
    file: UploadFile,
    manager: JobManager = Depends(get_job_manager),
) -> MetricsResponse:
    """Upload a reference DSM GeoTIFF to compute validation metrics against predicted elevations."""
    job_dir = manager.get_job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "EMPTY_FILE", "detail": "Reference file is empty"},
        )

    ref_path = job_dir / "reference.tif"
    with open(ref_path, "wb") as f:
        f.write(content)

    # Read reference raster
    try:
        with rasterio.open(str(ref_path)) as ref_src:
            ref_data = ref_src.read(1).astype(np.float32)
            ref_nodata = ref_src.nodata
    except Exception as e:
        ref_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "CORRUPT_REFERENCE", "detail": f"Cannot open reference DSM: {e}"},
        ) from e

    # Read predicted DSM
    dsm_path = job_dir / "dsm.tif"
    if not dsm_path.exists():
        dsm_path = job_dir / "rdsm.tif"

    if not dsm_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Predicted DSM not found for this job yet.",
        )

    with rasterio.open(str(dsm_path)) as pred_src:
        pred_data = pred_src.read(1).astype(np.float32)

    # Resize reference to match pred shape if necessary
    if ref_data.shape != pred_data.shape:
        import cv2

        ref_data = cv2.resize(
            ref_data,
            (pred_data.shape[1], pred_data.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )

    # Create valid mask
    mask = np.isfinite(pred_data) & np.isfinite(ref_data)
    if ref_nodata is not None:
        mask = mask & (~np.isclose(ref_data, ref_nodata))
    mask = mask & (pred_data != -9999.0)

    metrics_abs = compute_elevation_metrics(pred_data, ref_data, mask=mask)

    response = MetricsResponse(
        job_id=job_id,
        status="EVALUATED",
        metrics_absolute=metrics_abs,
        terrain_tag="urban_dense" if metrics_abs.get("rmse", 0) > 3.0 else "plains_open",
    )

    metrics_file = job_dir / "metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, indent=2)

    return response


@router.get("/{job_id}/metrics", response_model=MetricsResponse)
def get_job_metrics(
    job_id: str,
    manager: JobManager = Depends(get_job_manager),
) -> MetricsResponse:
    """Retrieve pre-computed validation metrics for a job."""
    metrics_file = manager.get_job_dir(job_id) / "metrics.json"
    if not metrics_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation metrics not found for job {job_id}. Please upload a reference DSM first.",
        )

    with open(metrics_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MetricsResponse(**data)


@router.post("/{job_id}/gcps", response_model=JobStatusResponse)
def recalibrate_with_gcps(
    job_id: str,
    payload: GcpPayload,
    manager: JobManager = Depends(get_job_manager),
) -> JobStatusResponse:
    """Recalibrate height estimation using supplied Ground Control Points (Path B) and re-export artifacts."""
    state = manager.get_job(job_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    if len(payload.gcps) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Path B calibration requires at least 3 non-collinear GCPs.",
        )

    job_dir = manager.get_job_dir(job_id)
    dsm_path = job_dir / "dsm.tif"
    if not dsm_path.exists():
        dsm_path = job_dir / "rdsm.tif"

    if not dsm_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No predicted DSM found to recalibrate.",
        )

    with rasterio.open(str(dsm_path)) as src:
        disparity = src.read(1)
        crs = src.crs
        transform = src.transform

    pts = [{"x": float(p.x), "y": float(p.y), "z_true": float(p.z_true)} for p in payload.gcps]
    cal_dsm, meta_b = calibrate_path_b(disparity, pts)

    # Re-export rasters
    export_job_rasters(
        output_dir=job_dir,
        dsm=cal_dsm,
        crs=crs,
        transform=transform,
        is_georeferenced=(crs is not None),
        metadata=meta_b,
        calibration_status="path_b_gcps",
    )

    # Re-export meshes
    input_file = next((f for f in job_dir.iterdir() if f.stem == "input"), None)
    if input_file:
        from depthwizard.io.readers import read_image_rgb

        rgb, _ = read_image_rgb(input_file)
        export_all_lod_glbs(
            heightmap=cal_dsm,
            rgb_image=rgb,
            out_dir=job_dir,
            gsd_m=0.33,
        )

    updated_state = manager.update_job(
        job_id=job_id,
        stage="DONE",
        progress=100,
        status="DONE",
        metadata_update={"calibration": meta_b, "recalibrated_via": "PATH_B"},
    )
    return JobStatusResponse(**updated_state)
