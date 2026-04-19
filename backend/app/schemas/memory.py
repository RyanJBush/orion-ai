from pydantic import BaseModel, Field


class MemoryWriteRequest(BaseModel):
    namespace: str
    key: str
    text: str
    metadata: dict = Field(default_factory=dict)


class VectorWriteRequest(BaseModel):
    namespace: str
    text: str


class MemorySearchRequest(BaseModel):
    namespace: str
    query: str


class MemoryResult(BaseModel):
    id: int
    score: float
    text: str
