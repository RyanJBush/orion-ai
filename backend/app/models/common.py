from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TaskStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    planning = "planning"
    running = "running"
    completed = "completed"
    failed = "failed"


class WorkflowRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    blocked = "blocked"
    retrying = "retrying"
    completed = "completed"
    failed = "failed"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    blocked = "blocked"
    retrying = "retrying"
    completed = "completed"
    failed = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
