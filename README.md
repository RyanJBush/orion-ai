# Orion AI Monorepo

Production-style monorepo for an agentic workflow platform with FastAPI, React, PostgreSQL, workflow orchestration, tool abstraction, and memory services.

## What is implemented
- Task submission and orchestration entrypoint (`POST /api/v1/tasks/submit`)
- Planner agent for step decomposition
- Worker agents for tool-driven step execution
- Tool abstraction layer with registry + default tools (`echo`, `math`)
- Workflow execution engine with run/step state tracking
- Basic memory + vector memory APIs and persistence models
- SQLAlchemy models/repositories for tasks, runs, steps, agents, memory
- Structured logging + startup DB initialization
- Docker Compose, Makefile targets, and CI scaffold

## Repository layout
```text
backend/      FastAPI API + orchestration runtime
frontend/     React/Vite UI scaffold
docs/         Architecture and API docs
.github/      CI workflows
```

## Local run
### Docker
```bash
make up
```

### Local dev
```bash
make install
make dev-backend
# another terminal
make dev-frontend
```

## API snapshot
- `POST /api/v1/tasks/submit`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/workflows/runs/{run_id}`
- `POST /api/v1/memory/basic/write`
- `POST /api/v1/memory/vector/write`
- `POST /api/v1/memory/vector/search`

See `docs/api.md` for full list.
