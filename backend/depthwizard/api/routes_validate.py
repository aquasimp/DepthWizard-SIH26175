"""API routes for reference DSM validation and GCP recalibration."""

import json
import logging

import matplotlib
import numpy as np
import rasterio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from PIL import Image

from depthwizard.api.routes_jobs import get_job_manager
from depthwizard.api.schemas import GcpPayload, JobStatusResponse, MetricsResponse
from depthwizard.calibration.gcp_fit import calibrate_path_b
from depthwizard.eval.coregister import coregister_grids
from depthwizard.eval.metrics import compute_elevation_metrics, compute_error_histogram
from depthwizard.io.writers import export_job_rasters, write_geotiff
from depthwizard.jobs.manager import JobManager
from depthwizard.mesh.export_glb import export_all_lod_glbs

logger = logging.getLogger(__name__)

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
    is_optical = False
    try:
        with rasterio.open(str(ref_path)) as ref_src:
            if ref_src.count >= 3 and ref_src.dtypes[0] == "uint8":
                is_optical = True
            else:
                ref_data = ref_src.read(1).astype(np.float32)
                ref_nodata = ref_src.nodata
    except Exception as e:
        ref_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "CORRUPT_REFERENCE", "detail": f"Cannot open reference DSM: {e}"},
        ) from e

    if is_optical:
        ref_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "OPTICAL_IMAGE_NOT_DEM",
                "detail": "Uploaded reference raster has 3 optical uint8 bands (RGB imagery), not a 1-band digital elevation model (DEM/LiDAR). Please upload a 1-band GeoTIFF containing metric elevation values.",
            },
        )

    # Read predicted DSM or nDSM based on reference base elevation
    dsm_path = job_dir / "dsm.tif"
    ndsm_path = job_dir / "ndsm.tif"
    if not dsm_path.exists():
        dsm_path = job_dir / "rdsm.tif"

    if not dsm_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Predicted DSM not found for this job yet.",
        )

    # If both absolute DSM and normalized nDSM exist, select the one that aligns with reference datum
    if ndsm_path.exists() and dsm_path.name == "dsm.tif":
        ref_valid = ref_data[np.isfinite(ref_data) & (ref_data != -9999.0)]
        if ref_valid.size > 0 and ref_valid.min() >= -0.5:
            try:
                with rasterio.open(str(dsm_path)) as dsm_src, rasterio.open(str(ndsm_path)) as ndsm_src:
                    d_mean = float(np.nanmean(dsm_src.read(1)))
                    n_mean = float(np.nanmean(ndsm_src.read(1)))
                    r_mean = float(np.nanmean(ref_valid))
                    if abs(n_mean - r_mean) < abs(d_mean - r_mean):
                        dsm_path = ndsm_path
            except Exception as e:
                logger.warning(f"Datum alignment comparison failed, defaulting to dsm.tif: {e}")

    with rasterio.open(str(dsm_path)) as pred_src:
        pred_data = pred_src.read(1).astype(np.float32)
        pred_crs = pred_src.crs
        pred_transform = pred_src.transform

    # Resize reference to match pred shape if necessary
    if ref_data.shape != pred_data.shape:
        import cv2

        ref_data = cv2.resize(
            ref_data,
            (pred_data.shape[1], pred_data.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )

    # Co-register reference grid to prediction grid
    pred_data, aligned_ref, shift_info = coregister_grids(pred_data, ref_data)

    # Create valid mask
    mask = (
        np.isfinite(pred_data)
        & np.isfinite(aligned_ref)
        & (pred_data != -9999.0)
        & (aligned_ref != -9999.0)
    )
    if ref_nodata is not None:
        mask = mask & (~np.isclose(aligned_ref, ref_nodata))

    # If predicted DSM is a relative uncalibrated heightmap (Path D, e.g. rdsm.tif with values in [0, 1])
    # fit a least-squares affine scale & shift to ground truth metric elevations.
    is_relative = (dsm_path.name == "rdsm.tif")
    if is_relative and mask.sum() > 10:
        p_valid = pred_data[mask]
        r_valid = aligned_ref[mask]
        p_span = float(np.percentile(p_valid, 99) - np.percentile(p_valid, 1))
        r_span = float(np.percentile(r_valid, 99) - np.percentile(r_valid, 1))
        if p_span > 1e-4 and r_span > 1.0:
            A = np.vstack([p_valid, np.ones_like(p_valid)]).T
            scale, shift = np.linalg.lstsq(A, r_valid, rcond=None)[0]
            if scale > 0:
                pred_data[mask] = (pred_data[mask] * scale + shift).astype(np.float32)
                shift_info["relative_calibration"] = {
                    "applied": True,
                    "scale": round(float(scale), 4),
                    "shift_m": round(float(shift), 4),
                    "note": "Path D relative disparity scaled to ground truth elevation datum",
                }

    metrics_abs = compute_elevation_metrics(pred_data, aligned_ref, mask=mask)

    # Compute signed difference: pred - ref
    diff_data = np.full_like(pred_data, -9999.0, dtype=np.float32)
    diff_data[mask] = pred_data[mask] - aligned_ref[mask]

    # Error distribution histogram (-15m to +15m)
    hist = compute_error_histogram(diff_data[mask], num_bins=50, range_m=(-15.0, 15.0))

    # Write difference GeoTIFF
    diff_tif_path = job_dir / "diff.tif"
    try:
        write_geotiff(
            path=diff_tif_path,
            data=diff_data,
            crs=pred_crs,
            transform=pred_transform,
            nodata=-9999.0,
            description="DSM_error_pred_minus_ref_meters",
        )
    except Exception as e:
        logger.warning(f"Failed to write difference GeoTIFF: {e}")

    # Generate colored difference preview PNG using RdBu_r (-15m to +15m)
    try:
        norm = np.clip((diff_data + 15.0) / 30.0, 0.0, 1.0)
        cmap = matplotlib.colormaps["RdBu_r"]
        rgba = cmap(norm)
        # Transparent for nodata / invalid pixels
        rgba[~mask] = [0.0, 0.0, 0.0, 0.0]
        rgba_img = (rgba * 255).astype(np.uint8)
        img_out = Image.fromarray(rgba_img)
        img_out.save(job_dir / "diff.png", format="PNG")
    except Exception as e:
        logger.warning(f"Failed to write difference PNG preview: {e}")

    # Determine terrain tag based on roughness / RMSE
    tag = "urban_dense" if metrics_abs.get("rmse", 0) > 3.0 else "plains_open"

    response = MetricsResponse(
        job_id=job_id,
        status="EVALUATED",
        metrics_absolute=metrics_abs,
        terrain_tag=tag,
        shift_applied=shift_info,
        histogram=hist,
        diff_artifact_url=f"/api/jobs/{job_id}/artifacts/diff.png",
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
