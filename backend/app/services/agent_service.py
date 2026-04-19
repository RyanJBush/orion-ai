from sqlalchemy.orm import Session

from app.models.agent import AgentModel
from app.schemas.agent import AgentCreate


class AgentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_agents(self) -> list[AgentModel]:
        return self.db.query(AgentModel).order_by(AgentModel.id.desc()).all()

    def create_agent(self, payload: AgentCreate) -> AgentModel:
        row = AgentModel(name=payload.name, role=payload.role)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
