# Orion AI Monorepo

Production-style monorepo for an agentic workflow platform with FastAPI, React, PostgreSQL, workflow orchestration, tool abstraction, approval gates, audit logging, and memory services.

## What is implemented

- Task submission and orchestration entrypoint (`POST /api/v1/tasks/submit`)
- Planner agent for step decomposition
- Worker agents for tool-driven step execution
- Tool abstraction layer with registry + default tools (`echo`, `math`, `flaky`, `slow_echo`, `sensitive_echo`)
- Workflow execution engine with retries, fallback actions, timeline events, and run controls
- Basic + vector memory APIs with persistence models
- Approval requests/decisions for sensitive tools
- Usage quotas and audit logging endpoints
- SQLAlchemy models/repositories for tasks, runs, steps, agents, approvals, usage, and memory
- Structured logging + startup DB initialization
- Docker Compose, Makefile targets, and CI scaffold

## Repository layout

```text
backend/      FastAPI API + orchestration runtime
frontend/     React/Vite UI
docs/         Architecture and API docs
.github/      CI workflows
```

## Local run

### Docker (recommended)

```bash
make up
```

This starts:

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:5432`

### Local development

```bash
make setup
cp backend/.env.example backend/.env
make dev-backend
# another terminal
make dev-frontend
```

### Checks

```bash
make test
make lint
```

## API snapshot

- `POST /api/v1/tasks/submit`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/workflows/runs/{run_id}`
- `GET /api/v1/workflows/runs/{run_id}/timeline`
- `GET /api/v1/workflows/runs/{run_id}/metrics`
- `POST /api/v1/approvals`
- `POST /api/v1/memory/basic/write`
- `POST /api/v1/memory/vector/write`
- `POST /api/v1/memory/vector/search`

See `docs/api.md` for the full list.
