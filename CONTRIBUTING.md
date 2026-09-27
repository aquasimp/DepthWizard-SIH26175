# Contributing to DepthWizard

Thank you for your interest in contributing to **DepthWizard**, developed for Smart India Hackathon 2026 (Problem Statement 26175, ISRO / Space Applications Centre).

---

## 1. Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- GDAL C libraries (via OS or bundled rasterio wheels)
- NVIDIA GPU with CUDA 12.4+ (optional, CPU fallback fully supported)

### Local Environment Setup
```bash
# Clone the repository
git clone https://github.com/aquasimp/DepthWizard-SIH26175.git
cd DepthWizard-SIH26175

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements-dev.txt

# Download base foundation weights
bash models/download_weights.sh

# Install frontend dependencies
cd frontend && npm install && cd ..
```

---

## 2. Verification & Testing Standards

Every contribution must pass the full verification suite before submission:

### Python Backend Tests
```bash
python -m pytest tests/ -v
```
All 75 test cases across 20 test modules must pass with zero failures.

### Frontend Tests
```bash
cd frontend && npm run test:run && cd ..
```
All Vitest unit and integration suites must pass.

### Code Quality & Static Analysis
```bash
# Linting
ruff check backend/depthwizard

# Type Checking
mypy backend/depthwizard
```

### Architectural & Scope Integrity
```bash
# Verify baseline scope fence integrity (zero unauthorized modifications)
python scripts/verify_scope_fence.py

# Verify bitwise encoder weights invariance
python scripts/audit_weights_v110.py
```

---

## 3. Pull Request Guidelines

1. **Feature Branches**: Branch from `master` using descriptive names (e.g., `feat/`, `fix/`, `docs/`).
2. **Honest Metrics**: Any PR modifying model training or calibration must include traceable, reproducible quantitative evaluations matching the standards in `docs/MODEL_CARD.md`.
3. **Licensing**: All contributions must be compatible with DepthWizard's **MIT License** and preserve Apache-2.0 upstream attribution for Depth Anything V3.
