from sqlalchemy.orm import Session

from app.models.workflow import WorkflowModel
from app.schemas.workflow import WorkflowCreate


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_workflows(self) -> list[WorkflowModel]:
        return self.db.query(WorkflowModel).order_by(WorkflowModel.id.desc()).all()

    def create_workflow(self, payload: WorkflowCreate) -> WorkflowModel:
        row = WorkflowModel(name=payload.name, description=payload.description)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
