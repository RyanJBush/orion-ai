from sqlalchemy.orm import Session

from app.models.common import TaskStatus
from app.models.task import TaskModel


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, title: str, description: str | None) -> TaskModel:
        task = TaskModel(title=title, description=description, status=TaskStatus.queued)
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
