"""Core processing pipeline coordinating detection, inference, calibration, and meshing."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from depthwizard.calibration.selector import calibrate_scene
from depthwizard.depth.infer import get_inference_engine
from depthwizard.io.gsd import resample_to_canonical_gsd
from depthwizard.io.readers import read_image_rgb
from depthwizard.io.writers import export_job_rasters
from depthwizard.jobs.manager import JobManager, gpu_semaphore
from depthwizard.mesh.export_glb import export_all_lod_glbs
from depthwizard.utils.logging import logger


def run_pipeline(
    job_id: str,
    file_path: Union[str, Path],
    options: Optional[Dict[str, Any]] = None,
    manager: Optional[JobManager] = None,
) -> Dict[str, Any]:
    """Execute end-to-end processing pipeline for a single remote sensing job.

    Chain:
      input -> detect -> gsd normalise -> tile -> infer -> calibrate -> write DSM -> mesh + texture -> artefacts

    Args:
        job_id: Unique job identifier.
        file_path: Path to input raster imagery file.
        options: Dictionary of user options (assumed_gsd_m, calibration_path, z_exag, gcps, etc.).
        manager: Optional JobManager instance (creates default if None).

    Returns:
        Final job status dictionary.
    """
    opts = options or {}
    mgr = manager or JobManager()
    job_dir = mgr.get_job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. PREPROCESS
        mgr.update_job(job_id, stage="PREPROCESS", progress=10)
        assumed_gsd = float(opts.get("assumed_gsd_m", 0.33))
        rgb, meta = read_image_rgb(file_path, max_upload_px=8000, assumed_gsd_m=assumed_gsd)

        is_georef = bool(meta.get("is_georeferenced", False))
        crs = meta.get("crs_obj")
        transform = meta.get("transform")
        gsd_m = float(meta.get("gsd", assumed_gsd))

        if is_georef and transform is not None:
            canon_rgb, resample_meta = resample_to_canonical_gsd(
                rgb, current_gsd=gsd_m, target_gsd=0.33
            )
            scale = resample_meta["resample_factor"]
            if abs(scale - 1.0) < 0.01:
                canon_transform = transform
            else:
                import rasterio
                h_orig, w_orig = rgb.shape[:2]
                h_new, w_new = canon_rgb.shape[:2]
                new_a = transform.a * (w_orig / max(1, w_new))
                new_e = transform.e * (h_orig / max(1, h_new))
                canon_transform = rasterio.Affine(new_a, transform.b, transform.c, transform.d, new_e, transform.f)
            canon_gsd = 0.33
        else:
            canon_rgb = rgb
            canon_transform = transform
            canon_gsd = gsd_m

        mgr.update_job(
            job_id,
            stage="PREPROCESS",
            progress=25,
            metadata_update={
                "is_georeferenced": is_georef,
                "gsd_m": canon_gsd,
                "width": canon_rgb.shape[1],
                "height": canon_rgb.shape[0],
            },
        )

        # 2. INFER (Serialized under GPU Semaphore)
        mgr.update_job(job_id, stage="INFER", progress=30)
        with gpu_semaphore:
            mgr.update_job(job_id, stage="INFER", progress=40)
            device = str(opts.get("device", "auto"))
            engine = get_inference_engine(mode="metric", device=device)
            raw_depth, wall_time = engine.infer_scene(canon_rgb, tile_size=512, overlap=64)

        mgr.update_job(
            job_id,
            stage="INFER",
            progress=60,
            metadata_update={"infer_time_seconds": round(wall_time, 2)},
        )

        # 3. CALIBRATE
        mgr.update_job(job_id, stage="CALIBRATE", progress=65)
        dsm, ndsm, calib_meta = calibrate_scene(
            disparity=raw_depth,
            is_georeferenced=is_georef,
            crs=crs,
            transform=canon_transform,
            bounds=meta.get("bounds"),
            gcps=opts.get("gcps"),
            reference_dsm=opts.get("reference_dsm"),
            explicit_path=opts.get("calibration_path"),
            gsd_m=canon_gsd,
        )
        mgr.update_job(
            job_id,
            stage="CALIBRATE",
            progress=75,
            metadata_update={"calibration": calib_meta},
        )

        # 4. EXPORT (GeoTIFF / 16-bit PNG Heightmap)
        mgr.update_job(job_id, stage="EXPORT", progress=78)
        export_job_rasters(
            output_dir=job_dir,
            dsm=dsm,
            ndsm=ndsm,
            crs=crs,
            transform=canon_transform,
            is_georeferenced=is_georef,
            metadata=calib_meta,
            assumed_gsd_m=canon_gsd,
        )
        mgr.update_job(job_id, stage="EXPORT", progress=85)

        # 5. MESH (Decimation into 3 LODs + Textured GLBs)
        mgr.update_job(job_id, stage="MESH", progress=88)
        z_exag = float(opts.get("z_exag", 1.0))
        export_all_lod_glbs(
            heightmap=dsm,
            rgb_image=canon_rgb,
            out_dir=job_dir,
            gsd_m=canon_gsd,
            z_exag=z_exag,
        )
        mgr.update_job(job_id, stage="MESH", progress=98)

        # 6. DONE
        artifacts_list = [p.name for p in job_dir.iterdir() if p.is_file() and p.name != "status.json"]
        return mgr.update_job(
            job_id,
            stage="DONE",
            progress=100,
            status="DONE",
            metadata_update={"artifacts": sorted(artifacts_list)},
        )

    except Exception as err:
        logger.exception(f"Job {job_id} processing failed: {err}")
        mgr.update_job(
            job_id,
            stage="FAILED",
            progress=0,
            status="FAILED",
            error=str(err),
        )
        raise
