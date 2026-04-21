from sqlalchemy.orm import Session

from app.models.common import ApprovalStatus
from app.models.workflow import ToolApprovalModel


class ToolApprovalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_request(self, run_id: int, step_id: str, tool_name: str, requested_by: str, reason: str | None) -> ToolApprovalModel:
        row = ToolApprovalModel(
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            requested_by=requested_by,
            reason=reason,
            status=ApprovalStatus.pending,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get(self, approval_id: int) -> ToolApprovalModel | None:
        return self.db.get(ToolApprovalModel, approval_id)

    def list_for_run(self, run_id: int) -> list[ToolApprovalModel]:
        return self.db.query(ToolApprovalModel).filter(ToolApprovalModel.run_id == run_id).order_by(ToolApprovalModel.id.desc()).all()

    def resolve(self, row: ToolApprovalModel, status: ApprovalStatus, reviewed_by: str) -> ToolApprovalModel:
        row.status = status
        row.reviewed_by = reviewed_by
        self.db.commit()
        self.db.refresh(row)
        return row

    def has_approved(self, run_id: int, step_id: str, tool_name: str) -> bool:
        row = (
            self.db.query(ToolApprovalModel)
            .filter(ToolApprovalModel.run_id == run_id)
            .filter(ToolApprovalModel.step_id == step_id)
            .filter(ToolApprovalModel.tool_name == tool_name)
            .filter(ToolApprovalModel.status == ApprovalStatus.approved)
            .first()
        )
        return row is not None
