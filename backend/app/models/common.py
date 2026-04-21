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
    paused = "paused"
    blocked = "blocked"
    retrying = "retrying"
    completed = "completed"
    canceled = "canceled"
    failed = "failed"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    blocked = "blocked"
    retrying = "retrying"
    completed = "completed"
    canceled = "canceled"
    failed = "failed"


class TaskPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class MemoryScope(str, Enum):
    short_term = "short_term"
    long_term = "long_term"


class MemoryType(str, Enum):
    fact = "fact"
    preference = "preference"
    prior_output = "prior_output"
    tool_result = "tool_result"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
