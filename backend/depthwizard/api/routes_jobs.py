"""API routes for job lifecycle management."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
