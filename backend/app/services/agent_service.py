from sqlalchemy.orm import Session

from app.models.agent import AgentModel
from app.schemas.agent import AgentCreate

_DEMO_AGENTS = [
    {"name": "planner", "role": "planner", "model": "gpt-4.1-mini"},
    {"name": "worker-general", "role": "executor", "model": "gpt-4.1-mini"},
    {"name": "worker-math", "role": "executor", "model": "gpt-4.1-mini"},
    {"name": "reviewer", "role": "reviewer", "model": "gpt-4.1-mini"},
]


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

    def seed_demo_agents(self) -> list[AgentModel]:
        """Insert the canonical demo agents if they don't already exist."""
        existing_names = {row.name for row in self.list_agents()}
        created: list[AgentModel] = []
        for spec in _DEMO_AGENTS:
            if spec["name"] in existing_names:
                continue
            row = AgentModel(name=spec["name"], role=spec["role"], model=spec["model"])
            self.db.add(row)
            created.append(row)
        if created:
            self.db.commit()
            for row in created:
                self.db.refresh(row)
        return [r for r in self.list_agents() if r.name in {s["name"] for s in _DEMO_AGENTS}]
