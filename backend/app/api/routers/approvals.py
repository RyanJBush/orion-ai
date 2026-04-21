from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.common import ApprovalStatus
from app.schemas.approval import ToolApprovalDecision, ToolApprovalRequestCreate, ToolApprovalResponse
from app.services.approval_service import ToolApprovalService

router = APIRouter()


@router.post("", response_model=ToolApprovalResponse)
def create_tool_approval(payload: ToolApprovalRequestCreate, db: Session = Depends(get_db)) -> ToolApprovalResponse:
    return ToolApprovalService(db).request(payload)


@router.post("/{approval_id}/decision", response_model=ToolApprovalResponse)
def decide_tool_approval(approval_id: int, payload: ToolApprovalDecision, db: Session = Depends(get_db)) -> ToolApprovalResponse:
    if payload.status == ApprovalStatus.pending:
        raise HTTPException(status_code=422, detail="Decision status cannot be pending")
    resolved = ToolApprovalService(db).decide(approval_id, payload)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return resolved


@router.get("/runs/{run_id}", response_model=list[ToolApprovalResponse])
def list_tool_approvals(run_id: int, db: Session = Depends(get_db)) -> list[ToolApprovalResponse]:
    return ToolApprovalService(db).list_for_run(run_id)
