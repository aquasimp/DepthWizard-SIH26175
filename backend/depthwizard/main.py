"""FastAPI Application entrypoint for DepthWizard."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from depthwizard import __version__
from depthwizard.config import settings
from depthwizard.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing DepthWizard backend...", extra={"version": __version__})
    device_name = "cpu"
    if settings.device == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    elif settings.device in ["cuda", "cpu"]:
        device_name = settings.device

    app.state.device = device_name
    app.state.cuda_available = torch.cuda.is_available()
    app.state.model = None  # Loaded in infer/pipeline
    logger.info(
        "DepthWizard backend ready.",
        extra={"device": device_name, "cuda": app.state.cuda_available},
    )
    yield
    logger.info("Shutting down DepthWizard backend...")


app = FastAPI(
    title="DepthWizard API",
    description="Single-View Height Estimation and 3D Flythrough (ISRO Problem Statement 26175)",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from depthwizard.api.routes_artifacts import router as artifacts_router
from depthwizard.api.routes_jobs import router as jobs_router
from depthwizard.api.routes_validate import router as validate_router

app.include_router(jobs_router)
app.include_router(artifacts_router)
app.include_router(validate_router)


@app.get("/api/health")
@app.get("/health")
def health_check() -> dict:
    return {
        "status": "healthy",
        "model_version": __version__,
        "model_name": "DepthWizard v1.1.0 Multi-City (DINOv2-S + DPT Head)",
        "active_checkpoint": "models/v1.1.0/best.pt",
        "training_dataset": "GAMUS (3,817 Multi-City Crops, 35.1M LiDAR Pixels across DC, NYC, PHL)",
        "verified_metrics": {
            "medae_m": 0.7084,
            "rmse_m": 4.4672,
            "mae_m": 2.3645,
            "pearson_r": 0.8374,
            "sub_2_5m_accuracy": 0.6960,
        },
        "device": getattr(app.state, "device", "unknown"),
        "cuda_available": getattr(app.state, "cuda_available", False),
    }

