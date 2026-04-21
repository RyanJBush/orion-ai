from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.memory import (
    MemoryCorrectionRequest,
    MemoryResult,
    MemorySearchRequest,
    MemorySummaryResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
    VectorWriteRequest,
)
from app.services.memory_service import MemoryService

router = APIRouter()


@router.post("/basic/write")
def write_basic_memory(payload: MemoryWriteRequest, db: Session = Depends(get_db)) -> MemoryWriteResponse:
    return MemoryService(db).write_basic(payload)


@router.post("/vector/write")
def write_vector_memory(payload: VectorWriteRequest, db: Session = Depends(get_db)) -> MemoryWriteResponse:
    return MemoryService(db).write_vector(payload)


@router.post("/vector/search", response_model=list[MemoryResult])
def search_vector_memory(payload: MemorySearchRequest, db: Session = Depends(get_db)) -> list[MemoryResult]:
    return MemoryService(db).search_vector(payload)


@router.post("/basic/{entry_id}/correct", response_model=MemoryWriteResponse)
def correct_basic_memory(entry_id: int, payload: MemoryCorrectionRequest, db: Session = Depends(get_db)) -> MemoryWriteResponse:
    corrected = MemoryService(db).correct_basic_memory(entry_id, payload)
    if corrected is None:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return corrected


@router.get("/summary/{namespace}", response_model=MemorySummaryResponse)
def summarize_memory(namespace: str, db: Session = Depends(get_db)) -> MemorySummaryResponse:
    return MemoryService(db).summarize_namespace(namespace)
