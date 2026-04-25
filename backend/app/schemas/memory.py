from datetime import datetime

from pydantic import BaseModel, Field

from app.models.common import MemoryScope, MemoryType


class MemoryWriteRequest(BaseModel):
    namespace: str
    key: str
    text: str
    scope: MemoryScope = MemoryScope.short_term
    memory_type: MemoryType = MemoryType.fact
    source_ref: str | None = None
    ttl_seconds: int | None = None
    metadata: dict = Field(default_factory=dict)


class VectorWriteRequest(BaseModel):
    namespace: str
    text: str
    scope: MemoryScope = MemoryScope.short_term
    memory_type: MemoryType = MemoryType.tool_result
    source_ref: str | None = None
    ttl_seconds: int | None = None
    metadata: dict = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    namespace: str
    query: str
    scope: MemoryScope | None = None
    memory_type: MemoryType | None = None


class MemoryResult(BaseModel):
    id: int
    score: float
    text: str
    scope: MemoryScope | None = None
    memory_type: MemoryType | None = None


class MemoryCorrectionRequest(BaseModel):
    replacement_text: str
    source_ref: str | None = None


class MemorySummaryResponse(BaseModel):
    namespace: str
    total_entries: int
    by_scope: dict[str, int]
    by_type: dict[str, int]
    latest_texts: list[str]


class MemoryWriteResponse(BaseModel):
    id: int
    namespace: str
    key: str | None = None
    scope: MemoryScope
    memory_type: MemoryType
    expires_at: datetime | None = None
