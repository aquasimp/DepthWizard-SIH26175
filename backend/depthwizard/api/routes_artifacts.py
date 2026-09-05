"""API routes for serving static job artifacts."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/jobs", tags=["artifacts"])
