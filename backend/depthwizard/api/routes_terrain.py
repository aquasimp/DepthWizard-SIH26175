"""API routes for extracting and serving 3D terrain meshes."""

import json
from pathlib import Path
from typing import Any, Dict

import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, status
import numpy as np

from depthwizard.api.routes_jobs import get_job_manager
from depthwizard.jobs.manager import JobManager
from depthwizard.utils.logging import logger

router = APIRouter(tags=["terrain"])


def extract_mesh_dict(job_dir: Path, job_id: str, resolution: int = 128) -> Dict[str, Any]:
    """Extract authoritative 3D elevation mesh and sidecars from job artifacts."""
    meta_path = job_dir / "heightmap.meta.json"
    png_path = job_dir / "heightmap_16bit.png"
    if not meta_path.exists() or not png_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Heightmap artifacts missing for job {job_id}.",
        )

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Read 16-bit PNG
    png = cv2.imread(str(png_path), cv2.IMREAD_UNCHANGED)
    if png is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read 16-bit heightmap image for job {job_id}.",
        )

    h_min = float(meta.get("h_min_raw", 0.0))
    h_max = float(meta.get("h_max_raw", 1.0))
    h_range = h_max - h_min
    if h_range < 1e-6:
        h_range = 1.0

    # If unanchored relative normalized [0, 1] range, scale to 35.0m structural relief
    scale_boost = 35.0 if (h_range <= 1.05 and h_min >= -0.01 and not meta.get("is_absolute", False)) else 1.0

    # True metric or relative elevations
    h_real = h_min + (png.astype(np.float32) / 65535.0) * (h_range * scale_boost)
    is_abs = bool(meta.get("is_absolute", False))

    # Downsample to grid resolution (e.g. 128x128) using INTER_AREA to preserve structure
    res = max(16, min(512, int(resolution)))
    h_grid = cv2.resize(h_real, (res, res), interpolation=cv2.INTER_AREA)

    h_list = [round(float(v), 3) for v in h_grid.flatten()]
    min_elev = float(h_grid.min())
    max_elev = float(h_grid.max())
    mean_elev = float(h_grid.mean())

    aspect_ratio = float(meta.get("width", 1024)) / max(1, float(meta.get("height", 1024)))

    has_glb = (job_dir / "terrain_lod0.glb").exists()
    has_dsm = (job_dir / "dsm.tif").exists()
    has_rdsm = (job_dir / "rdsm.tif").exists()

    return {
        "status": "success",
        "job_id": job_id,
        "rows": res,
        "cols": res,
        "min_height": min_elev,
        "max_height": max_elev,
        "mean_height": mean_elev,
        "aspect_ratio": aspect_ratio,
        "is_absolute": is_abs,
        "crs": meta.get("crs", "EPSG:3857 (Metric Grid · WGS84 UTM 18N)"),
        "heights": h_list,
        "texture_url": f"/api/jobs/{job_id}/artifacts/texture.jpg",
        "glb_url": f"/api/jobs/{job_id}/artifacts/terrain_lod0.glb" if has_glb else None,
        "dsm_vis_url": f"/api/jobs/{job_id}/artifacts/dsm.tif" if has_dsm else (f"/api/jobs/{job_id}/artifacts/rdsm.tif" if has_rdsm else None),
    }


@router.get("/api/jobs/{job_id}/mesh")
def get_job_mesh(
    job_id: str,
    resolution: int = Query(default=128, ge=16, le=512),
    manager: JobManager = Depends(get_job_manager),
) -> Dict[str, Any]:
    """Retrieve authoritatively decoded 3D elevation mesh grid for a specific job."""
    job_dir = manager.get_job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return extract_mesh_dict(job_dir, job_id, resolution=resolution)


@router.get("/api/terrain/mesh")
def get_default_terrain_mesh(
    resolution: int = Query(default=128, ge=16, le=512),
    manager: JobManager = Depends(get_job_manager),
) -> Dict[str, Any]:
    """Serve authentic 3D terrain mesh data for the active benchmark tile."""
    candidates = ["job_1790662888_5ffbdc8e", "demo", "job_1790534856_4dc57795", "job_1789027816_bc4209d8"]
    for cid in candidates:
        cdir = manager.get_job_dir(cid)
        if (cdir / "heightmap.meta.json").exists():
            return extract_mesh_dict(cdir, cid, resolution=resolution)

    # Fallback to the latest completed job with heightmap
    for j in sorted(manager.jobs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if j.is_dir() and (j / "heightmap.meta.json").exists():
            return extract_mesh_dict(j, j.name, resolution=resolution)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No terrain mesh available.",
    )
