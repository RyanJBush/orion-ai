# Orion AI

Orion AI is a production-style monorepo for a multi-agent workflow orchestration platform.

## Monorepo layout

```text
.
├── backend
├── docs
├── frontend
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
└── docker-compose.yml
```

## Tech stack

- **Backend:** FastAPI + Python
- **AI orchestration:** LangChain primitives + planner/worker workflow engine
- **Database:** PostgreSQL (via docker-compose), SQLAlchemy models
- **Memory:** FAISS vector store
- **Auth:** JWT with RBAC checks
- **Frontend:** React + Vite + Tailwind CSS
- **Infra:** Docker, docker-compose, GitHub Actions
- **Quality:** pytest, ruff, eslint, prettier

## Quick start

```bash
make setup
make dev
```

The backend will run on `http://localhost:8000` and frontend on `http://localhost:5173`.

See `/docs` for architecture notes.
