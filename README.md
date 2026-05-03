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
- `POST /api/v1/workflows/runs/{run_id}/replay`
- `POST /api/v1/workflows/templates/seed-demo`
- `POST /api/v1/approvals`
- `POST /api/v1/memory/basic/write`
- `POST /api/v1/memory/vector/write`
- `POST /api/v1/memory/vector/search`

See `docs/api.md` for the full list.

## Demo script (portfolio-ready flow)

1. Start services with `make up` (or run backend/frontend locally via dev commands).
2. Seed templates:
   ```bash
   make demo-seed
   ```
3. List templates and capture one `id`:
   ```bash
   curl http://localhost:8000/api/v1/workflows/templates
   ```
4. Execute template run:
   ```bash
   curl -X POST http://localhost:8000/api/v1/workflows/templates/<id>/run
   ```
5. Inspect run timeline, metrics, and insights:
   ```bash
   curl http://localhost:8000/api/v1/workflows/runs/<run_id>/timeline
   curl http://localhost:8000/api/v1/workflows/runs/<run_id>/metrics
   curl http://localhost:8000/api/v1/workflows/runs/<run_id>/insights
   ```

Use the **Workflow Execution** page in the frontend to load the same run ID and demonstrate pause/resume/cancel/replay controls with live telemetry.

## Demo workflows

Seed and run production-like demo scenarios:

- `POST /api/v1/workflows/templates/seed-demo` to install research, analysis, and multi-step reasoning templates.
- `POST /api/v1/workflows/templates/{template_id}/run` to execute one-click demo runs.
- Use Workflow Execution View in frontend to inspect graph, timeline, and per-step detail panel.

