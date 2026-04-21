from fastapi import APIRouter

from app.schemas.tool import ToolHealthResponse, ToolSchemaResponse
from app.tools.registry import tool_registry

router = APIRouter()


@router.get("/registry", response_model=list[ToolSchemaResponse])
def get_tool_registry() -> list[ToolSchemaResponse]:
    return [ToolSchemaResponse.model_validate(schema.__dict__) for schema in tool_registry.list_schemas()]


@router.get("/health", response_model=list[ToolHealthResponse])
def get_tool_health() -> list[ToolHealthResponse]:
    rows = tool_registry.health()
    return [ToolHealthResponse.model_validate(row) for row in rows]
