from sqlalchemy import case
from sqlalchemy.orm import Session

from app.models.common import TaskPriority, TaskStatus
from app.models.task import TaskModel


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, title: str, description: str | None, priority: TaskPriority) -> TaskModel:
        task = TaskModel(title=title, description=description, status=TaskStatus.queued, priority=priority)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: int) -> TaskModel | None:
        return self.db.get(TaskModel, task_id)

    def list(self) -> list[TaskModel]:
        return self.db.query(TaskModel).order_by(TaskModel.id.desc()).all()

    def set_status(self, task: TaskModel, status: TaskStatus) -> TaskModel:
        task.status = status
        self.db.commit()
        self.db.refresh(task)
        return task

    def pop_next_queued(self) -> TaskModel | None:
        priority_order = case(
            (TaskModel.priority == TaskPriority.urgent, 0),
            (TaskModel.priority == TaskPriority.high, 1),
            (TaskModel.priority == TaskPriority.normal, 2),
            else_=3,
        )
        return (
            self.db.query(TaskModel)
            .filter(TaskModel.status == TaskStatus.queued)
            .order_by(priority_order.asc(), TaskModel.id.asc())
            .first()
        )
