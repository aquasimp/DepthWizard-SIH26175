# 07 — Standalone Deployment Guide

DepthWizard is designed for single-command deployment across both local workstations and air-gapped demo environments.

---

## 1. Quickstart with Docker Compose

### Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.20+
- (Optional for GPU acceleration) NVIDIA Container Toolkit (`nvidia-docker2`)

### Method A: GPU Deployment (NVIDIA CUDA)
```bash
# Clone the repository
git clone https://github.com/depthwizard/depthwizard.git
cd depthwizard

# Download weights if not already present
bash models/download_weights.sh

# Launch full stack (FastAPI backend + Nginx frontend)
docker compose up --build
```
The application will be live at:
- **Frontend**: `http://localhost:8080`
- **Backend API Docs**: `http://localhost:8000/docs`

### Method B: CPU-Only Deployment (Offline / No GPU)
```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build
```

---

## 2. Bare-Metal Local Development Setup

### Windows (PowerShell) / Linux / macOS
```bash
# 1. Initialize environment and dependencies
make setup

# 2. Run both backend and frontend in development mode
make dev
```
Or manually:
```bash
# Terminal 1: Backend
uv venv .venv
uv pip install -p .venv -r backend/requirements-dev.txt
.venv\Scripts\python -m uvicorn depthwizard.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

---

## 3. Offline Venue Operation & SRTM Cache
DepthWizard is packaged with pre-cached SRTM GL1 30 m DEM tiles in `data/cache/srtm/` for demo Areas of Interest (AOIs).
If network access is unavailable, the pipeline automatically detects cached tiles without issuing outbound HTTP requests.
