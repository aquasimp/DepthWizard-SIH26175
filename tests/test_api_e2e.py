"""End-to-end integration tests for FastAPI backend and JobManager."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from depthwizard.jobs.manager import JobManager
from depthwizard.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path):
    """Create test client with isolated jobs directory."""
    jobs_dir = tmp_path / "test_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    manager = JobManager(jobs_dir=jobs_dir)
    app.state.job_manager = manager

    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client: TestClient):
    """Assert health endpoint returns 200 and valid schema."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "model_version" in data
    assert "device" in data
    assert "cuda_available" in data


def test_api_invalid_corrupt_upload_returns_422(client: TestClient, fixtures_dir: Path):
    """Assert invalid and corrupt uploads return HTTP 422 with structured error bodies."""
    # 1. Corrupt image file
    corrupt_path = fixtures_dir / "corrupt.tif"
    with open(corrupt_path, "rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"file": ("corrupt.tif", f, "image/tiff")},
        )
    assert resp.status_code == 422
    err = resp.json()
    assert "detail" in err
    assert err["detail"].get("error_code") == "CORRUPT_IMAGE"

    # 2. Empty file
    resp_empty = client.post(
        "/api/jobs",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert resp_empty.status_code == 422
    err_empty = resp_empty.json()
    assert err_empty["detail"].get("error_code") == "EMPTY_FILE"


def test_api_e2e_upload_poll_done(client: TestClient):
    """POST a sample -> poll until DONE -> assert artifacts exist and are non-empty."""
    sample_path = Path("data/samples/sample_georeferenced.tif")
    if not sample_path.exists():
        pytest.skip("Sample georeferenced file not found")

    with open(sample_path, "rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"file": ("sample_georeferenced.tif", f, "image/tiff")},
            data={"assumed_gsd_m": "0.33", "z_exag": "1.0"},
        )
    assert resp.status_code == 201
    create_data = resp.json()
    job_id = create_data["job_id"]
    assert job_id.startswith("job_")
    assert create_data["status"] == "PENDING"

    # Poll status until DONE or FAILED (max 45 seconds)
    start_time = time.time()
    final_state = None
    while time.time() - start_time < 45.0:
        status_resp = client.get(f"/api/jobs/{job_id}")
        assert status_resp.status_code == 200
        state = status_resp.json()
        if state["status"] in ("DONE", "FAILED"):
            final_state = state
            break
        time.sleep(0.5)

    assert final_state is not None, "Pipeline timed out before reaching terminal status"
    assert final_state["status"] == "DONE", f"Pipeline failed: {final_state.get('error')}"
    assert final_state["progress"] == 100

    # Assert critical artifacts exist and are non-empty
    manager: JobManager = app.state.job_manager
    job_dir = manager.get_job_dir(job_id)

    dsm_tif = job_dir / "dsm.tif"
    heightmap_png = job_dir / "heightmap_16bit.png"
    mesh_lod0 = job_dir / "terrain_lod0.glb"

    assert dsm_tif.exists() and dsm_tif.stat().st_size > 0, "dsm.tif missing or empty"
    assert heightmap_png.exists() and heightmap_png.stat().st_size > 0, "heightmap_16bit.png missing or empty"
    assert mesh_lod0.exists() and mesh_lod0.stat().st_size > 0, "terrain_lod0.glb missing or empty"

    # Test artifact download via HTTP GET
    art_resp = client.get(f"/api/jobs/{job_id}/artifacts/terrain_lod0.glb")
    assert art_resp.status_code == 200
    assert len(art_resp.content) == mesh_lod0.stat().st_size

    # Test reference DSM upload & validation metrics
    with open(dsm_tif, "rb") as f_ref:
        ref_resp = client.post(
            f"/api/jobs/{job_id}/reference",
            files={"file": ("reference.tif", f_ref, "image/tiff")},
        )
    assert ref_resp.status_code == 200
    metrics_data = ref_resp.json()
    assert metrics_data["status"] == "EVALUATED"
    assert "metrics_absolute" in metrics_data
    assert metrics_data["metrics_absolute"]["rmse"] >= 0.0

    # Test GET /api/jobs/{job_id}/metrics
    get_metrics_resp = client.get(f"/api/jobs/{job_id}/metrics")
    assert get_metrics_resp.status_code == 200
    assert get_metrics_resp.json()["metrics_absolute"]["mae"] == metrics_data["metrics_absolute"]["mae"]


def test_concurrent_posts_serialize_gracefully(client: TestClient):
    """Assert concurrent POST requests serialize gracefully under gpu_semaphore without error."""
    sample_path = Path("data/samples/sample_georeferenced.tif")
    if not sample_path.exists():
        pytest.skip("Sample georeferenced file not found")

    def submit_job(idx: int):
        with open(sample_path, "rb") as f:
            r = client.post(
                "/api/jobs",
                files={"file": (f"sample_{idx}.tif", f, "image/tiff")},
                data={"assumed_gsd_m": "0.33"},
            )
        return r.status_code, r.json().get("job_id")

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_job, 1)
        f2 = executor.submit(submit_job, 2)
        code1, j1 = f1.result()
        code2, j2 = f2.result()

    assert code1 == 201 and code2 == 201
    assert j1 != j2

    # Verify both jobs eventually reach DONE without deadlock
    start_time = time.time()
    for jid in [j1, j2]:
        done = False
        while time.time() - start_time < 60.0:
            status_resp = client.get(f"/api/jobs/{jid}")
            state = status_resp.json()
            if state["status"] == "DONE":
                done = True
                break
            time.sleep(0.5)
        assert done, f"Concurrent job {jid} did not complete"
