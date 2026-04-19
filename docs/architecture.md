# Orion AI Architecture

## Core Runtime Flow
1. Client submits a task via `POST /tasks/submit`.
2. `WorkflowEngine` marks task + run state and invokes `PlannerAgent`.
3. Planner decomposes task into ordered steps with tool actions.
4. Worker agents execute steps through `ToolRegistry`.
5. Step outputs are persisted and written to vector memory.
6. Run + task statuses are finalized and queryable by API.

## Backend Layering
- **API Routers**: HTTP contracts and request validation.
- **Services**: domain orchestration (`WorkflowEngine`, `TaskService`, `MemoryService`).
- **Repositories**: SQLAlchemy persistence boundaries.
- **Agents**: planner and worker execution logic.
- **Tools**: pluggable abstraction with registry.
- **Models**: task, workflow run, execution step, memory, agent tables.

## Memory Design
- **Basic memory**: key-value style storage (`memory_entries`).
- **Vector memory**: lightweight embedding + cosine similarity search (`vector_memory`).
