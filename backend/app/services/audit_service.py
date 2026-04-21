import re

from sqlalchemy.orm import Session

from app.repositories.audit_repository import AuditLogRepository
from app.schemas.audit import AuditLogCreate, AuditLogResponse


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditLogRepository(db)

    @staticmethod
    def redact(text: str) -> str:
        redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", text)
        redacted = re.sub(r"\b\d{12,16}\b", "****", redacted)
        return redacted

    def write(self, payload: AuditLogCreate) -> AuditLogResponse:
        row = self.repo.create(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            action=payload.action,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            details=payload.details,
            summary=self.redact(payload.summary),
        )
        return AuditLogResponse.model_validate(row)

    def list(self, workspace_id: str | None = None, limit: int = 50) -> list[AuditLogResponse]:
        return [AuditLogResponse.model_validate(row) for row in self.repo.list_logs(workspace_id=workspace_id, limit=limit)]
