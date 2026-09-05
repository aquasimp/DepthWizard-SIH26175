"""Pytest configuration and test fixtures for DepthWizard."""

import sys
from pathlib import Path

import pytest

# Ensure backend and repo_root are on python path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


@pytest.fixture
def fixtures_dir() -> Path:
    p = repo_root / "tests" / "fixtures"
    p.mkdir(parents=True, exist_ok=True)
    if not (p / "projected_metres.tif").exists():
        from tests.fixtures.generate_fixtures import generate_all_fixtures

        generate_all_fixtures(p)
    return p


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    out = tmp_path / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out
