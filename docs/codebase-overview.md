# Codebase Overview

This document summarizes how Orion AI is organized across backend, frontend, and infrastructure.

## Top-level layout

- `backend/`: FastAPI service implementing task submission, workflow orchestration, tools, approvals, memory, usage, and audit APIs.
- `frontend/`: React + Vite UI for dashboard, tasks, workflow execution, agent monitor, and settings.
- `docs/`: architecture and API docs.
- root `docker-compose.yml` + `Makefile`: local orchestration and developer commands.

## Backend structure

- `app/main.py`: app factory, router wiring, startup DB initialization, health check.
- `app/api/routers/`: versioned route handlers by domain (`tasks`, `workflows`, `memory`, `tools`, `approvals`, `audit`, `usage`, `agents`).
- `app/services/`: orchestration/business logic (`WorkflowEngine`, `TaskService`, `MemoryService`, etc.).
- `app/repositories/`: SQLAlchemy persistence operations by aggregate.
- `app/models/`: SQLAlchemy table models and shared enums.
- `app/schemas/`: request/response contracts.
- `app/agents/`: planner/worker agent abstractions.
- `app/tools/`: tool interfaces, registry, and demo tool implementations.
- `app/db/`: engine/session/base and initialization.

## Runtime flow

1. Client submits a task.
2. Planner decomposes task text into steps.
3. Workflow engine persists steps and executes dependency-ready work.
4. Worker agents invoke named tools through the registry.
5. Results, timeline events, audit records, and memory entries are persisted.
6. Run can be paused/resumed/canceled/replayed and inspected via API.

## Frontend structure

- `src/App.tsx`: route-level page composition.
- `src/pages/`: page containers for major product surfaces.
- `src/components/`: reusable UI components including workflow execution panels.
- `src/services/api.ts`: typed API client wrappers.
- `src/types/`: domain types shared by UI components.

## Key technologies

- Backend: Python 3.11+, FastAPI, Pydantic settings, SQLAlchemy 2.x, psycopg.
- Frontend: React 18, React Router, TypeScript, Vite.
- Data store: PostgreSQL (Docker) with SQLite default fallback for local config.
- Testing/linting: pytest + ruff (backend), eslint + tsc build (frontend).
