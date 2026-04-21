import logging

from sqlalchemy.orm import Session

from app.models.common import TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import Task, TaskCreate

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: Session) -> None:
        self.repo = TaskRepository(db)

    def list_tasks(self) -> list[Task]:
        return [Task.model_validate(row) for row in self.repo.list()]

    def create_task(self, payload: TaskCreate) -> Task:
        row = self.repo.create(payload.title, payload.description, payload.priority)
        logger.info("task.created", extra={"task_id": row.id})
        return Task.model_validate(row)

    def get_task(self, task_id: int) -> Task | None:
        row = self.repo.get(task_id)
        return Task.model_validate(row) if row else None

    def set_status(self, task_id: int, status: TaskStatus) -> Task | None:
        row = self.repo.get(task_id)
        if not row:
            return None
        updated = self.repo.set_status(row, status)
        logger.info("task.status_updated", extra={"task_id": task_id, "status": status.value})
        return Task.model_validate(updated)

    def pop_next_queued_task(self) -> Task | None:
        row = self.repo.pop_next_queued()
        return Task.model_validate(row) if row else None
