import logging

from sqlalchemy.orm import Session

from app.agents.planner_agent import planner_agent
from app.agents.worker_agent import WorkerAgent
from app.models.common import StepStatus, TaskStatus, WorkflowRunStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository
from app.schemas.memory import VectorWriteRequest
from app.schemas.workflow import WorkflowRun
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.run_repo = WorkflowRunRepository(db)
        self.memory_service = MemoryService(db)

    def execute_task(self, task_id: int, workflow_name: str = "default") -> WorkflowRun:
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        self.task_repo.set_status(task, TaskStatus.planning)
        run = self.run_repo.create_run(workflow_name=workflow_name, task_id=task_id)
        self.run_repo.set_run_status(run, WorkflowRunStatus.running)

        logger.info("workflow.started", extra={"run_id": run.id, "task_id": task.id})

        plan = planner_agent.decompose(task.title, task.description)
        self.task_repo.set_status(task, TaskStatus.running)

        for planned_step in plan:
            step = self.run_repo.add_step(
                run_id=run.id,
                step_order=planned_step.order,
                worker_name=planned_step.worker_name,
                action=planned_step.action,
                input_text=planned_step.instruction,
                status=StepStatus.running,
            )
            worker = WorkerAgent(name=planned_step.worker_name)
            try:
                result = worker.execute(action=planned_step.action, instruction=planned_step.instruction)
                self.run_repo.update_step(step, StepStatus.completed, result.output)
                self.memory_service.write_vector(
                    payload=VectorWriteRequest(namespace=f"task:{task_id}", text=f"{planned_step.instruction} -> {result.output}")
                )
            except Exception as exc:  # noqa: BLE001
                self.run_repo.update_step(step, StepStatus.failed, str(exc))
                self.run_repo.set_run_status(run, WorkflowRunStatus.failed)
                self.task_repo.set_status(task, TaskStatus.failed)
                logger.exception("workflow.step_failed", extra={"run_id": run.id, "step_id": step.id})
                raise

        self.run_repo.set_run_status(run, WorkflowRunStatus.completed)
        self.task_repo.set_status(task, TaskStatus.completed)
        logger.info("workflow.completed", extra={"run_id": run.id, "task_id": task.id})

        return WorkflowRun.model_validate(self.run_repo.get_run(run.id))

    def get_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        return WorkflowRun.model_validate(run) if run else None
