# Orion API Endpoints

Base path: `/api/v1`

## Health

- `GET /healthz`

## Tasks

- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/submit` (creates task + runs planner/worker workflow)
- `POST /tasks/enqueue`
- `POST /tasks/dispatch-next`

## Workflows

- `GET /workflows`
- `POST /workflows`
- `GET /workflows/templates`
- `POST /workflows/templates`
- `POST /workflows/templates/seed-demo`
- `POST /workflows/templates/{template_id}/run`
- `GET /workflows/runs/{run_id}`
- `GET /workflows/runs/{run_id}/timeline`
- `GET /workflows/runs/{run_id}/metrics`
- `GET /workflows/runs/{run_id}/insights`
- `POST /workflows/runs/{run_id}/pause`
- `POST /workflows/runs/{run_id}/resume`
- `POST /workflows/runs/{run_id}/cancel`
- `POST /workflows/runs/{run_id}/replay`
- `GET /workflows/metrics`

## Agents

- `GET /agents`
- `POST /agents`

## Tools

- `GET /tools/registry`
- `GET /tools/health`

## Approvals

- `POST /approvals`
- `POST /approvals/{approval_id}/decision`
- `GET /approvals/runs/{run_id}`

## Memory

- `POST /memory/basic/write`
- `POST /memory/vector/write`
- `POST /memory/vector/search`
- `POST /memory/basic/{entry_id}/correct`
- `GET /memory/summary/{namespace}`

## Audit

- `POST /audit`
- `GET /audit`

## Usage

- `GET /usage/quota/{actor_id}`
- `POST /usage/quota`
