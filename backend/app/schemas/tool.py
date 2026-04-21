from pydantic import BaseModel, Field


class ToolSchemaResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, str] = Field(default_factory=dict)
    output_schema: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float
    allowed_workers: list[str] = Field(default_factory=list)
    is_demo_tool: bool = False
    requires_approval: bool = False
    risk_level: str = "low"


class ToolHealthResponse(BaseModel):
    tool: str
    healthy: bool
    status: str
