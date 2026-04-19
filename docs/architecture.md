# Orion AI MVP Architecture

## Backend

- FastAPI app exposing task/workflow/agent/memory APIs
- SQLAlchemy models: `users`, `tasks`, `workflows`, `agents`, `tool_calls`, `memory`
- JWT auth with role checks (`admin`, `operator`, `viewer`)
- Workflow engine:
  - planner splits task into steps
  - worker agents execute tool calls
  - memory service persists summaries in FAISS + relational DB

## Frontend

- React + Vite + Tailwind single-page app
- Views: Login, Dashboard, Tasks, Workflow View, Agent Monitor, Settings
- Live status cards for tasks/workflows/agents + execution logs

## Infrastructure

- Dockerfiles for backend/frontend
- docker-compose for full-stack local run
- GitHub Actions CI for lint + tests
