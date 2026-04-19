from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import Agent, AgentCreate
from app.services.agent_service import AgentService

router = APIRouter()


@router.get("", response_model=list[Agent])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    rows = AgentService(db).list_agents()
    return [Agent.model_validate(row) for row in rows]


@router.post("", response_model=Agent)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    row = AgentService(db).create_agent(payload)
    return Agent.model_validate(row)
