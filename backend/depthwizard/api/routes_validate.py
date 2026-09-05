"""API routes for reference DSM validation and GCP fitting."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/jobs", tags=["validation"])
