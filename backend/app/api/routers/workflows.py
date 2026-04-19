from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.workflow import WorkflowCreate, WorkflowRun
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.get("")
def list_workflows(db: Session = Depends(get_db)) -> list[dict]:
    rows = WorkflowService(db).list_workflows()
    return [{"id": row.id, "name": row.name, "description": row.description} for row in rows]


@router.post("")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> dict:
    row = WorkflowService(db).create_workflow(payload)
    return {"id": row.id, "name": row.name, "description": row.description}


@router.get("/runs/{run_id}", response_model=WorkflowRun)
def get_workflow_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRun:
    run = WorkflowEngine(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run
