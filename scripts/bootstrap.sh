#!/usr/bin/env bash
set -euo pipefail

echo "=== DepthWizard Bootstrap ==="
PYTHON="${PYTHON:-python3}"

# 1. Setup virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate || source .venv/Scripts/activate

# 2. Install backend dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements-dev.txt
pip install -e .

# 3. Download weights
echo "Fetching pretrained weights..."
bash models/download_weights.sh

# 4. Setup frontend
echo "Installing frontend dependencies..."
cd frontend
npm install
npm run build
cd ..

echo "=== DepthWizard Bootstrap Complete ==="
echo "To start development servers: make dev"
