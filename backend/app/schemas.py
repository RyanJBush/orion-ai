from datetime import datetime

from pydantic import BaseModel, Field

from app.models import TaskStatus, WorkflowStatus


class LoginRequest(BaseModel):
    email: str
    role: str = "operator"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecuteRequest(BaseModel):
    task_id: int


class WorkflowResponse(BaseModel):
    id: int
    task_id: int
    plan: str
    status: WorkflowStatus
    execution_log: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    id: int
    name: str
    role: str
    status: str

    class Config:
        from_attributes = True


class MemoryResponse(BaseModel):
    task_id: int
    entries: list[str]
