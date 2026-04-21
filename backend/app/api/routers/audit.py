from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.audit import AuditLogCreate, AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("", response_model=AuditLogResponse)
def create_audit_log(payload: AuditLogCreate, db: Session = Depends(get_db)) -> AuditLogResponse:
    return AuditService(db).write(payload)


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    return AuditService(db).list(workspace_id=workspace_id, limit=limit)
