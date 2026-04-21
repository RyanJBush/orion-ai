from sqlalchemy.orm import Session

from app.models.workflow import WorkflowTemplateModel


class WorkflowTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_templates(self) -> list[WorkflowTemplateModel]:
        return self.db.query(WorkflowTemplateModel).order_by(WorkflowTemplateModel.id.desc()).all()

    def get(self, template_id: int) -> WorkflowTemplateModel | None:
        return self.db.get(WorkflowTemplateModel, template_id)

    def create(
        self,
        *,
        name: str,
        description: str,
        task_title: str,
        task_description: str,
        workflow_name: str,
        tags: list[str],
        is_demo: bool,
    ) -> WorkflowTemplateModel:
        row = WorkflowTemplateModel(
            name=name,
            description=description,
            task_title=task_title,
            task_description=task_description,
            workflow_name=workflow_name,
            tags=tags,
            is_demo=is_demo,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
