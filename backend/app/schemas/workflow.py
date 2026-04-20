from datetime import datetime

from pydantic import BaseModel, Field

from app.models.common import StepStatus, WorkflowRunStatus


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None


class ExecutionStep(BaseModel):
    id: int
    step_id: str
    step_order: int
    worker_name: str
    action: str
    input_text: str
    dependencies: list[str] = Field(default_factory=list)
    expected_output: str
    completion_criteria: str
    output_text: str
    status: StepStatus
    attempt_count: int = 0
    max_retries: int = 0
    latency_ms: int | None = None
    fallback_action: str | None = None

    class Config:
        from_attributes = True


class WorkflowRun(BaseModel):
    id: int
    workflow_name: str
    task_id: int
    trace_id: str
    status: WorkflowRunStatus
    created_at: datetime | None = None
    steps: list[ExecutionStep] = Field(default_factory=list)

    class Config:
        from_attributes = True


class WorkflowTimelineEvent(BaseModel):
    id: int
    run_id: int
    step_id: int | None = None
    event_type: str
    message: str
    metadata: dict = Field(default_factory=dict, alias="event_metadata")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ToolReliabilityMetric(BaseModel):
    tool: str
    completed: int
    failed: int
    success_rate: float


class WorkflowMetrics(BaseModel):
    total_runs: int
    completion_rate: float
    retry_rate: float
    avg_step_latency_ms: float
    run_status_counts: dict[str, int]
    tool_reliability: list[ToolReliabilityMetric]
