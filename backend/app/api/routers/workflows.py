from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.common import StepStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel, WorkflowRunModel
from app.schemas.workflow import WorkflowCreate, WorkflowMetrics, WorkflowRun, WorkflowTimelineEvent, ToolReliabilityMetric
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


@router.get("/runs/{run_id}/timeline", response_model=list[WorkflowTimelineEvent])
def get_workflow_timeline(run_id: int, db: Session = Depends(get_db)) -> list[WorkflowTimelineEvent]:
    run = WorkflowEngine(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return WorkflowEngine(db).get_timeline(run_id)


@router.get("/metrics", response_model=WorkflowMetrics)
def get_workflow_metrics(db: Session = Depends(get_db)) -> WorkflowMetrics:
    status_rows = (
        db.query(WorkflowRunModel.status, func.count(WorkflowRunModel.id))
        .group_by(WorkflowRunModel.status)
        .all()
    )
    status_counts = {status.value: count for status, count in status_rows}
    total_runs = sum(status_counts.values())
    completed_runs = status_counts.get(WorkflowRunStatus.completed.value, 0)

    step_rows = (
        db.query(
            ExecutionStepModel.action,
            ExecutionStepModel.status,
            ExecutionStepModel.attempt_count,
            ExecutionStepModel.latency_ms,
        )
        .all()
    )
    total_steps = len(step_rows)
    retried_steps = sum(1 for row in step_rows if row.attempt_count > 1)
    latency_values = [row.latency_ms for row in step_rows if row.latency_ms is not None]

    tool_counts: dict[str, dict[str, int]] = {}
    for row in step_rows:
        tool_counts.setdefault(row.action, {"completed": 0, "failed": 0})
        if row.status == StepStatus.completed:
            tool_counts[row.action]["completed"] += 1
        if row.status == StepStatus.failed:
            tool_counts[row.action]["failed"] += 1

    reliability = [
        ToolReliabilityMetric(
            tool=tool,
            completed=counts["completed"],
            failed=counts["failed"],
            success_rate=(counts["completed"] / max(counts["completed"] + counts["failed"], 1)),
        )
        for tool, counts in sorted(tool_counts.items())
    ]

    return WorkflowMetrics(
        total_runs=total_runs,
        completion_rate=(completed_runs / total_runs) if total_runs else 0.0,
        retry_rate=(retried_steps / total_steps) if total_steps else 0.0,
        avg_step_latency_ms=(sum(latency_values) / len(latency_values)) if latency_values else 0.0,
        run_status_counts=status_counts,
        tool_reliability=reliability,
    )
