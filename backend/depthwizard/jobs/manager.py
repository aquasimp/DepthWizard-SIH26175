"""Job manager handling on-disk state persistence and concurrency."""

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Global semaphore to serialize all GPU execution
gpu_semaphore = threading.Semaphore(1)


class JobManager:
    """Manages on-disk state transitions for DepthWizard jobs.

    Pipeline stages:
      PENDING -> PREPROCESS -> INFER -> CALIBRATE -> EXPORT -> MESH -> DONE | FAILED
    """

    def __init__(self, jobs_dir: Optional[Union[str, Path]] = None):
        self.jobs_dir = Path(jobs_dir or "jobs")
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def get_job_dir(self, job_id: str) -> Path:
        """Get directory path for a specific job."""
        return self.jobs_dir / job_id

    def create_job(
        self,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new job with initial PENDING status."""
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        job_state: Dict[str, Any] = {
            "job_id": job_id,
            "status": "PENDING",
            "stage": "PENDING",
            "progress": 0,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {
                "input_filename": filename,
                "options": options or {},
                "artifacts": [],
            },
        }

        status_file = job_dir / "status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(job_state, f, indent=2)

        return job_id

    def update_job(
        self,
        job_id: str,
        stage: str,
        progress: int,
        status: Optional[str] = None,
        error: Optional[str] = None,
        metadata_update: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update job stage, progress, and metadata atomically."""
        job_dir = self.get_job_dir(job_id)
        status_file = job_dir / "status.json"

        with self._lock:
            if not status_file.exists():
                raise FileNotFoundError(f"Job not found: {job_id}")

            with open(status_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            state["stage"] = stage
            state["progress"] = max(0, min(100, int(progress)))

            if status is not None:
                state["status"] = status
            elif stage == "DONE":
                state["status"] = "DONE"
            elif stage == "FAILED":
                state["status"] = "FAILED"
            elif state["status"] == "PENDING" and stage != "PENDING":
                state["status"] = "PROCESSING"

            if error is not None:
                state["error"] = str(error)

            state["updated_at"] = datetime.now(timezone.utc).isoformat()

            if metadata_update:
                if "metadata" not in state or not isinstance(state["metadata"], dict):
                    state["metadata"] = {}
                state["metadata"].update(metadata_update)

            # Atomic write via temporary file
            temp_file = job_dir / f"status_{uuid.uuid4().hex[:6]}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(status_file)

            return state

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current state dictionary for a job."""
        status_file = self.get_job_dir(job_id) / "status.json"
        if not status_file.exists():
            return None

        try:
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all known jobs ordered by created_at descending."""
        jobs: List[Dict[str, Any]] = []
        if not self.jobs_dir.exists():
            return jobs

        for child in self.jobs_dir.iterdir():
            if child.is_dir():
                status_file = child / "status.json"
                if status_file.exists():
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            jobs.append(json.load(f))
                    except Exception:
                        continue

        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs
