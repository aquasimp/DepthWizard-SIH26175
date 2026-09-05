"""API routes for serving static job artifacts."""


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from depthwizard.api.routes_jobs import get_job_manager
from depthwizard.jobs.manager import JobManager

router = APIRouter(prefix="/api/jobs", tags=["artifacts"])


@router.get("/{job_id}/artifacts/{name}")
def get_artifact(
    job_id: str,
    name: str,
    manager: JobManager = Depends(get_job_manager),
) -> FileResponse:
    """Download or stream a generated artifact file for a job."""
    job_dir = manager.get_job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    # Security check to prevent directory traversal
    file_path = (job_dir / name).resolve()
    if not str(file_path).startswith(str(job_dir.resolve())):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Invalid artifact path.",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{name}' not found for job {job_id}.",
        )

    media_type = None
    suffix = file_path.suffix.lower()
    if suffix == ".glb":
        media_type = "model/gltf-binary"
    elif suffix in (".tif", ".tiff"):
        media_type = "image/tiff"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif suffix == ".json":
        media_type = "application/json"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=name,
    )
