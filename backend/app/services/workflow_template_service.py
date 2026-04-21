from sqlalchemy.orm import Session

from app.repositories.workflow_template_repository import WorkflowTemplateRepository
from app.schemas.task import TaskCreate
from app.schemas.workflow import WorkflowRun, WorkflowTemplate, WorkflowTemplateCreate
from app.services.task_service import TaskService
from app.services.workflow_engine import WorkflowEngine


class WorkflowTemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WorkflowTemplateRepository(db)

    def list_templates(self) -> list[WorkflowTemplate]:
        return [WorkflowTemplate.model_validate(row) for row in self.repo.list_templates()]

    def create_template(self, payload: WorkflowTemplateCreate) -> WorkflowTemplate:
        row = self.repo.create(
            name=payload.name,
            description=payload.description,
            task_title=payload.task_title,
            task_description=payload.task_description,
            workflow_name=payload.workflow_name,
            tags=payload.tags,
            is_demo=payload.is_demo,
        )
        return WorkflowTemplate.model_validate(row)

    def run_template(self, template_id: int) -> WorkflowRun | None:
        template = self.repo.get(template_id)
        if template is None:
            return None
        task = TaskService(self.db).create_task(
            TaskCreate(title=template.task_title, description=template.task_description)
        )
        return WorkflowEngine(self.db).execute_task(task.id, workflow_name=template.workflow_name)
