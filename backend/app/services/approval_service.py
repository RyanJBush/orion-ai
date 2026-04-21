from sqlalchemy.orm import Session

from app.models.common import ApprovalStatus
from app.repositories.approval_repository import ToolApprovalRepository
from app.schemas.approval import ToolApprovalDecision, ToolApprovalRequestCreate, ToolApprovalResponse


class ToolApprovalService:
    def __init__(self, db: Session) -> None:
        self.repo = ToolApprovalRepository(db)

    def request(self, payload: ToolApprovalRequestCreate) -> ToolApprovalResponse:
        row = self.repo.create_request(
            run_id=payload.run_id,
            step_id=payload.step_id,
            tool_name=payload.tool_name,
            requested_by=payload.requested_by,
            reason=payload.reason,
        )
        return ToolApprovalResponse.model_validate(row)

    def decide(self, approval_id: int, payload: ToolApprovalDecision) -> ToolApprovalResponse | None:
        if payload.status == ApprovalStatus.pending:
            return None
        row = self.repo.get(approval_id)
        if row is None:
            return None
        updated = self.repo.resolve(row, payload.status, payload.reviewed_by)
        return ToolApprovalResponse.model_validate(updated)

    def list_for_run(self, run_id: int) -> list[ToolApprovalResponse]:
        return [ToolApprovalResponse.model_validate(row) for row in self.repo.list_for_run(run_id)]

    def has_approval(self, run_id: int, step_id: str, tool_name: str) -> bool:
        return self.repo.has_approved(run_id=run_id, step_id=step_id, tool_name=tool_name)
