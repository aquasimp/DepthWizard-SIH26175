"""Pydantic request and response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: int = Field(ge=0, le=100)
    error: Optional[str] = None
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    model_version: str
    device: str
    cuda_available: bool
    status: str = "healthy"


class GcpPoint(BaseModel):
    x: float
    y: float
    z_true: float


class GcpPayload(BaseModel):
    gcps: List[GcpPoint]


class MetricsResponse(BaseModel):
    job_id: str
    status: str
    metrics_absolute: Optional[Dict[str, float]] = None
    metrics_ndsm: Optional[Dict[str, float]] = None
    breakdown_by_class: Optional[Dict[str, Dict[str, float]]] = None
    terrain_tag: Optional[str] = None
    shift_applied: Optional[Dict[str, Any]] = None
    histogram: Optional[Dict[str, Any]] = None
    diff_artifact_url: Optional[str] = None
