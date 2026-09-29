"""API routes for job lifecycle management."""

import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status

from depthwizard.api.schemas import JobCreateResponse, JobStatusResponse
from depthwizard.io.detect import CorruptImageError
from depthwizard.io.readers import ImageDimensionExceededError, NonNorthUpError, read_image_rgb
from depthwizard.jobs.manager import JobManager
from depthwizard.jobs.pipeline import run_pipeline
from depthwizard.utils.logging import logger

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Shared default job manager instance
_manager = JobManager()


def get_job_manager(request: Request) -> JobManager:
    """Dependency provider for JobManager."""
    return getattr(request.app.state, "job_manager", _manager)


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile,
    assumed_gsd_m: float = Form(default=0.33),
    calibration_path: Optional[str] = Form(default=None),
    z_exag: float = Form(default=0.2),
    model_version: Optional[str] = Form(default="v1.1.0_best"),
    manager: JobManager = Depends(get_job_manager),
) -> JobCreateResponse:
    """Upload imagery and launch asynchronous height estimation and meshing pipeline."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "INVALID_FILENAME", "detail": "Filename cannot be empty"},
        )

    # Read uploaded content into memory for validation
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "EMPTY_FILE", "detail": "Uploaded file is empty"},
        )

    # Temporary validate path
    ext = Path(file.filename).suffix or ".tif"
    temp_upload_dir = manager.jobs_dir / ".tmp_uploads"
    temp_upload_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_upload_dir / f"check_{file.filename}"
    with open(temp_file, "wb") as f:
        f.write(content)

    # Validate image readability and geometry
    try:
        read_image_rgb(temp_file, max_upload_px=8000, assumed_gsd_m=assumed_gsd_m)
    except CorruptImageError as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "CORRUPT_IMAGE", "detail": str(e)},
        ) from e
    except ImageDimensionExceededError as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "IMAGE_DIMENSION_EXCEEDED", "detail": str(e)},
        ) from e
    except NonNorthUpError as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "NON_NORTH_UP", "detail": str(e)},
        ) from e
    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "CORRUPT_IMAGE", "detail": f"Cannot parse input image: {e}"},
        ) from e

    # Create job entry
    options = {
        "assumed_gsd_m": assumed_gsd_m,
        "calibration_path": calibration_path,
        "z_exag": z_exag,
        "model_version": model_version or "v1.1.0_best",
    }
    job_id = manager.create_job(filename=file.filename, options=options)
    job_dir = manager.get_job_dir(job_id)

    # Persist input file in job directory
    final_input_path = job_dir / f"input{ext}"
    temp_file.replace(final_input_path)

    # Launch background thread to execute pipeline
    def worker() -> None:
        try:
            run_pipeline(
                job_id=job_id,
                file_path=final_input_path,
                options=options,
                manager=manager,
            )
        except Exception as err:
            logger.error(f"Background execution failed for {job_id}: {err}")

    thread = threading.Thread(target=worker, daemon=True, name=f"worker-{job_id}")
    thread.start()

    return JobCreateResponse(
        job_id=job_id,
        status="PENDING",
        message="Job created and queued for processing.",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    manager: JobManager = Depends(get_job_manager),
) -> JobStatusResponse:
    """Retrieve job progress, stage, status, and metadata."""
    state = manager.get_job(job_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} does not exist.",
        )

    return JobStatusResponse(**state)


@router.get("", response_model=list[JobStatusResponse])
def list_jobs(
    manager: JobManager = Depends(get_job_manager),
) -> list[JobStatusResponse]:
    """List all processing jobs."""
    jobs = manager.list_jobs()
    return [JobStatusResponse(**j) for j in jobs]
