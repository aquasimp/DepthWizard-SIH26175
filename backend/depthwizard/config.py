"""DepthWizard application settings and configurations."""

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

    opentopo_api_key: str = ""
    device: str = "auto"
    max_upload_px: int = 8000

    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    jobs_dir: Path = Path("jobs")
    models_dir: Path = Path("models")
    cache_dir: Path = Path("data/cache")
    samples_dir: Path = Path("data/samples")

    default_model_checkpoint: str = "models/depth_anything_v2_vits.pth"
    ft_model_checkpoint: str = "models/v1.1.0/best.pt"
    ft_tall_model_checkpoint: str = "models/v1.1.0/best_tall.pt"
    legacy_model_checkpoint: str = "models/dav2s_gamus_ft_v1.pth"
    model_version: str = "1.1.0"
    assumed_gsd_m: float = 0.33
    canonical_gsd_m: float = 0.33
    assumed_max_structure_height_m: float = 45.0


settings = Settings()

# Ensure directories exist
os.makedirs(settings.jobs_dir, exist_ok=True)
os.makedirs(settings.models_dir, exist_ok=True)
os.makedirs(settings.cache_dir / "srtm", exist_ok=True)
