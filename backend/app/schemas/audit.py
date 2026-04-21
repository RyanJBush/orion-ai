from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    workspace_id: str = "default"
    actor_id: str = "system"
    action: str
    resource_type: str
    resource_id: str
    details: dict = Field(default_factory=dict)
    summary: str = ""


class AuditLogResponse(BaseModel):
    id: int
    workspace_id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    details: dict = Field(default_factory=dict, alias="details_json")
    summary: str = Field(default="", alias="redacted_summary")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
