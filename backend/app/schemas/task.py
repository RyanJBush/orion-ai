from datetime import datetime

from pydantic import BaseModel, Field

from app.models.common import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=128)
    description: str | None = None


class TaskSubmitRequest(TaskCreate):
    workflow_name: str = "default"


class Task(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: TaskStatus
    created_at: datetime | None = None

    class Config:
        from_attributes = True
