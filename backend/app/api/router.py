from fastapi import APIRouter

from app.api.routers import agents, memory, tasks, workflows

api_router = APIRouter()
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
