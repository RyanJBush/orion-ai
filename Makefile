.PHONY: setup install install-backend install-frontend dev dev-backend dev-frontend test lint up down

setup: install

install: install-backend install-frontend

install-backend:
	cd backend && python -m pip install -e .[dev]

install-frontend:
	cd frontend && npm install

dev: dev-backend

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && PYTHONPATH=. pytest

lint:
	cd backend && ruff check app
	cd frontend && npm run lint

up:
	docker compose up --build

down:
	docker compose down -v
