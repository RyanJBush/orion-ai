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

    def seed_demo_templates(self) -> list[WorkflowTemplate]:
        demo_specs = [
            {
                "name": "demo-research-workflow",
                "description": "Research workflow with discovery, synthesis, and recommendation steps.",
                "task_title": "Research AI observability options",
                "task_description": "collect vendor landscape. then compare pricing 10 20 30. then draft recommendation",
                "workflow_name": "default",
                "tags": ["demo", "research"],
            },
            {
                "name": "demo-analysis-workflow",
                "description": "Analysis workflow with calculations and summary generation.",
                "task_title": "Analyze incident trends",
                "task_description": "compute incident totals 14 7 9. then summarize trend and risks",
                "workflow_name": "default",
                "tags": ["demo", "analysis"],
            },
            {
                "name": "demo-multi-step-reasoning",
                "description": "Multi-step reasoning workflow that chains dependent steps.",
                "task_title": "Reason through rollout plan",
                "task_description": "define goals. then identify blockers. then propose phased rollout",
                "workflow_name": "default",
                "tags": ["demo", "reasoning"],
            },
            {
                "name": "demo-kpi-report",
                "description": "End-to-end KPI report workflow with data extraction and calculations.",
                "task_title": "Generate KPI report",
                "task_description": "Collect metrics. calculate 12 + 30. then draft summary.",
                "workflow_name": "default",
                "tags": ["demo", "reporting"],
            },
            {
                "name": "demo-approval-flow",
                "description": "Sensitive action workflow demonstrating tool approvals and audit events.",
                "task_title": "Run approval workflow",
                "task_description": "perform sensitive export requiring approval",
                "workflow_name": "default",
                "tags": ["demo", "approval"],
            },
            {
                "name": "demo-retry-fallback",
                "description": "Resilience scenario showcasing retries and fallback actions.",
                "task_title": "Execute resilience workflow",
                "task_description": "flaky integration call. then summarize outcome",
                "workflow_name": "default",
                "tags": ["demo", "resilience"],
            },
        ]

        existing = {template.name for template in self.repo.list_templates()}
        created: list[WorkflowTemplate] = []
        for spec in demo_specs:
            if spec["name"] in existing:
                continue
            row = self.repo.create(
                name=spec["name"],
                description=spec["description"],
                task_title=spec["task_title"],
                task_description=spec["task_description"],
                workflow_name=spec["workflow_name"],
                tags=spec["tags"],
                is_demo=True,
            )
            created.append(WorkflowTemplate.model_validate(row))
        return created
