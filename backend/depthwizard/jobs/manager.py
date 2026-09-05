"""Job manager handling state persistence and concurrency."""

import threading
from typing import Optional

# Global semaphore to serialize all GPU execution
gpu_semaphore = threading.Semaphore(1)


class JobManager:
    """Manages on-disk state transitions for DepthWizard jobs."""

    def __init__(self, jobs_dir: Optional[str] = None):
        self.jobs_dir = jobs_dir or "jobs"
