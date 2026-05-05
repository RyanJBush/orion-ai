from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import Agent, AgentCreate
from app.services.agent_service import AgentService
from app.tools.registry import tool_registry

router = APIRouter()


@router.get("", response_model=list[Agent])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    rows = AgentService(db).list_agents()
    return [Agent.model_validate(row) for row in rows]


@router.post("", response_model=Agent)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    row = AgentService(db).create_agent(payload)
    return Agent.model_validate(row)


@router.post("/seed-demo", response_model=list[Agent])
def seed_demo_agents(db: Session = Depends(get_db)) -> list[Agent]:
    """Seed the three canonical demo agents (planner, worker-general, worker-math)."""
    return [Agent.model_validate(row) for row in AgentService(db).seed_demo_agents()]


@router.get("/stats")
def get_agent_stats(db: Session = Depends(get_db)) -> list[dict]:
    """Return agent rows enriched with tool-health status for the monitor page."""
    rows = AgentService(db).list_agents()
    tool_health = {entry["tool"]: entry["healthy"] for entry in tool_registry.health()}

    stats = []
    for row in rows:
        schemas = tool_registry.list_schemas()
        allowed_tools = [s.name for s in schemas if not s.allowed_workers or row.name in s.allowed_workers]
        all_healthy = all(tool_health.get(t, True) for t in allowed_tools)
        stats.append(
            {
                "id": row.id,
                "name": row.name,
                "role": row.role,
                "model": row.model,
                "status": "healthy" if all_healthy else "degraded",
                "allowed_tools": allowed_tools,
                "tool_count": len(allowed_tools),
            }
        )
    return stats
