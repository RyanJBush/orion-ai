from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.memory import MemoryResult, MemorySearchRequest, MemoryWriteRequest, VectorWriteRequest
from app.services.memory_service import MemoryService

router = APIRouter()


@router.post("/basic/write")
def write_basic_memory(payload: MemoryWriteRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    return MemoryService(db).write_basic(payload)


@router.post("/vector/write")
def write_vector_memory(payload: VectorWriteRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    return MemoryService(db).write_vector(payload)


@router.post("/vector/search", response_model=list[MemoryResult])
def search_vector_memory(payload: MemorySearchRequest, db: Session = Depends(get_db)) -> list[MemoryResult]:
    return MemoryService(db).search_vector(payload)
