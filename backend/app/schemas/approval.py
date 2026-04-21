from datetime import datetime

from pydantic import BaseModel

from app.models.common import ApprovalStatus


class ToolApprovalRequestCreate(BaseModel):
    run_id: int
    step_id: str
    tool_name: str
    requested_by: str = "operator"
    reason: str | None = None


class ToolApprovalDecision(BaseModel):
    status: ApprovalStatus
    reviewed_by: str


class ToolApprovalResponse(BaseModel):
    id: int
    run_id: int
    step_id: str
    tool_name: str
    status: ApprovalStatus
    requested_by: str
    reviewed_by: str | None = None
    reason: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
