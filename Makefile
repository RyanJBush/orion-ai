SHELL := /bin/bash

.PHONY: setup dev backend frontend lint test format

setup:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker compose up --build

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

test:
	cd backend && pytest -q

format:
	cd backend && ruff check --fix .
	cd frontend && npm run format
