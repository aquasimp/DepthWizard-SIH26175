.PHONY: setup dev test lint docker-up docker-up-cpu clean

PYTHON ?= python
VENV_PYTHON = .venv/bin/python
ifeq ($(OS),Windows_NT)
    VENV_PYTHON = .venv/Scripts/python.exe
endif

setup:
	uv venv .venv --python 3.11 || $(PYTHON) -m venv .venv
	uv pip install -p .venv -r backend/requirements-dev.txt || $(VENV_PYTHON) -m pip install -r backend/requirements-dev.txt
	bash models/download_weights.sh || $(VENV_PYTHON) models/download_weights.py
	cd frontend && npm install

dev:
	powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', '& $(VENV_PYTHON) -m uvicorn depthwizard.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload'; Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd frontend; npm run dev'"

test:
	$(VENV_PYTHON) -m pytest tests/ -v
	cd frontend && npm run test:run

lint:
	$(VENV_PYTHON) -m ruff check .
	$(VENV_PYTHON) -m mypy backend/depthwizard
	cd frontend && npx tsc --noEmit

docker-up:
	docker compose up --build

docker-up-cpu:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache frontend/dist
