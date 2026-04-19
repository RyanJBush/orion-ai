# Orion API Endpoints

Base path: `/api/v1`

## Tasks
- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/submit` (creates task + runs planner/worker workflow)

## Workflows
- `GET /workflows`
- `POST /workflows`
- `GET /workflows/runs/{run_id}`

## Agents
- `GET /agents`
- `POST /agents`

## Memory
- `POST /memory/basic/write`
- `POST /memory/vector/write`
- `POST /memory/vector/search`
