# Convenience targets for running the Zoetis RIE without Docker.
# Requires Python 3.11+ and Node 18+.

.PHONY: help install seeds backend frontend test build dev

help:
	@echo "Targets:"
	@echo "  make install   - install backend + frontend dependencies"
	@echo "  make seeds     - (re)generate the deterministic --seed 42 dataset"
	@echo "  make backend   - run the FastAPI backend on :8000"
	@echo "  make frontend  - run the Vite dev server on :5173 (proxies /api)"
	@echo "  make test      - run the backend pytest suite"
	@echo "  make build     - production build of the frontend"
	@echo "  make dev       - run backend + frontend together"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

seeds:
	cd backend && python -m app.data.generator --seed 42 --issues 30

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest -q

build:
	cd frontend && npm run build

# Run both; backend in the background, frontend in the foreground.
dev:
	cd backend && uvicorn app.main:app --port 8000 & \
	cd frontend && npm run dev
