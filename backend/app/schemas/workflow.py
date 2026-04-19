from datetime import datetime

from pydantic import BaseModel

from app.models.common import StepStatus, WorkflowRunStatus


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None


class ExecutionStep(BaseModel):
    id: int
    step_order: int
    worker_name: str
    action: str
    input_text: str
    output_text: str
    status: StepStatus

    class Config:
        from_attributes = True


class WorkflowRun(BaseModel):
    id: int
    workflow_name: str
    task_id: int
    status: WorkflowRunStatus
    created_at: datetime | None = None
    steps: list[ExecutionStep] = []

    class Config:
        from_attributes = True
