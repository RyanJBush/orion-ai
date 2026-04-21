from sqlalchemy.orm import Session

from app.models.audit import AuditLogModel


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        summary: str,
    ) -> AuditLogModel:
        row = AuditLogModel(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=details,
            redacted_summary=summary,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_logs(self, workspace_id: str | None = None, limit: int = 50) -> list[AuditLogModel]:
        query = self.db.query(AuditLogModel)
        if workspace_id:
            query = query.filter(AuditLogModel.workspace_id == workspace_id)
        return query.order_by(AuditLogModel.id.desc()).limit(limit).all()
