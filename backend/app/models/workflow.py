from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import StepStatus, TimestampMixin, WorkflowRunStatus


class WorkflowModel(TimestampMixin, Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowRunModel(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[WorkflowRunStatus] = mapped_column(
        Enum(WorkflowRunStatus), default=WorkflowRunStatus.pending, nullable=False
    )
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    task = relationship("TaskModel", back_populates="workflow_runs")
    steps = relationship("ExecutionStepModel", back_populates="run", cascade="all, delete-orphan")
    timeline_events = relationship("WorkflowTimelineEventModel", back_populates="run", cascade="all, delete-orphan")


class ExecutionStepModel(TimestampMixin, Base):
    __tablename__ = "execution_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=lambda: [], nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    completion_criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[StepStatus] = mapped_column(Enum(StepStatus), default=StepStatus.pending, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    backoff_seconds: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    fallback_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run = relationship("WorkflowRunModel", back_populates="steps")
    timeline_events = relationship("WorkflowTimelineEventModel", back_populates="step")


class WorkflowTimelineEventModel(Base):
    __tablename__ = "workflow_timeline_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[int | None] = mapped_column(ForeignKey("execution_steps.id", ondelete="CASCADE"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=lambda: {}, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run = relationship("WorkflowRunModel", back_populates="timeline_events")
    step = relationship("ExecutionStepModel", back_populates="timeline_events")
