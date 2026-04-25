from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.common import StepStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel, WorkflowRunModel
from app.schemas.workflow import (
    ToolReliabilityMetric,
    WorkflowCreate,
    WorkflowMetrics,
    WorkflowReplayRequest,
    WorkflowRun,
    WorkflowRunControlResponse,
    WorkflowRunInsight,
    WorkflowRunMetrics,
    WorkflowTemplate,
    WorkflowTemplateCreate,
    WorkflowTimelineEvent,
)
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_insight_service import WorkflowInsightService
from app.services.workflow_service import WorkflowService
from app.services.workflow_template_service import WorkflowTemplateService

router = APIRouter()


@router.get("")
def list_workflows(db: Session = Depends(get_db)) -> list[dict]:
    rows = WorkflowService(db).list_workflows()
    return [{"id": row.id, "name": row.name, "description": row.description} for row in rows]


@router.post("")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> dict:
    row = WorkflowService(db).create_workflow(payload)
    return {"id": row.id, "name": row.name, "description": row.description}


@router.get("/templates", response_model=list[WorkflowTemplate])
def list_workflow_templates(db: Session = Depends(get_db)) -> list[WorkflowTemplate]:
    return WorkflowTemplateService(db).list_templates()


@router.post("/templates", response_model=WorkflowTemplate)
def create_workflow_template(payload: WorkflowTemplateCreate, db: Session = Depends(get_db)) -> WorkflowTemplate:
    return WorkflowTemplateService(db).create_template(payload)


@router.post("/templates/seed-demo", response_model=list[WorkflowTemplate])
def seed_demo_workflow_templates(db: Session = Depends(get_db)) -> list[WorkflowTemplate]:
    return WorkflowTemplateService(db).seed_demo_templates()


@router.post("/templates/{template_id}/run", response_model=WorkflowRun)
def run_workflow_template(template_id: int, db: Session = Depends(get_db)) -> WorkflowRun:
    run = WorkflowTemplateService(db).run_template(template_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return run


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


@router.get("/runs/{run_id}/metrics", response_model=WorkflowRunMetrics)
def get_workflow_run_metrics(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunMetrics:
    run = WorkflowEngine(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    timeline = WorkflowEngine(db).get_timeline(run_id)
    fallback_step_ids = {event.step_id for event in timeline if event.metadata.get("used_fallback") and event.step_id}
    retried_steps = sum(1 for step in run.steps if step.attempt_count > 1)
    latency_values = [step.latency_ms for step in run.steps if step.latency_ms is not None]
    completed_steps = sum(1 for step in run.steps if step.status == StepStatus.completed)
    failed_steps = sum(1 for step in run.steps if step.status == StepStatus.failed)

    return WorkflowRunMetrics(
        run_id=run.id,
        trace_id=run.trace_id,
        total_steps=len(run.steps),
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        retried_steps=retried_steps,
        fallback_steps=len(fallback_step_ids),
        avg_step_latency_ms=(sum(latency_values) / len(latency_values)) if latency_values else 0.0,
    )


@router.get("/runs/{run_id}/insights", response_model=WorkflowRunInsight)
def get_workflow_run_insights(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunInsight:
    run = WorkflowEngine(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return WorkflowInsightService(db).build_insight(run)


@router.post("/runs/{run_id}/pause", response_model=WorkflowRunControlResponse)
def pause_workflow_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunControlResponse:
    run = WorkflowEngine(db).pause_run(run_id)
    if not run:
        raise HTTPException(status_code=409, detail="Workflow run cannot be paused")
    return WorkflowRunControlResponse(
        run_id=run.id,
        status=run.status,
        pause_requested=run.pause_requested,
        cancel_requested=run.cancel_requested,
    )


@router.post("/runs/{run_id}/resume", response_model=WorkflowRunControlResponse)
def resume_workflow_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunControlResponse:
    run = WorkflowEngine(db).resume_run(run_id)
    if not run:
        raise HTTPException(status_code=409, detail="Workflow run is not paused")
    return WorkflowRunControlResponse(
        run_id=run.id,
        status=run.status,
        pause_requested=run.pause_requested,
        cancel_requested=run.cancel_requested,
    )


@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunControlResponse)
def cancel_workflow_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRunControlResponse:
    run = WorkflowEngine(db).cancel_run(run_id)
    if not run:
        raise HTTPException(status_code=409, detail="Workflow run cannot be canceled")
    return WorkflowRunControlResponse(
        run_id=run.id,
        status=run.status,
        pause_requested=run.pause_requested,
        cancel_requested=run.cancel_requested,
    )


@router.post("/runs/{run_id}/replay", response_model=WorkflowRun)
def replay_workflow_run(
    run_id: int,
    payload: WorkflowReplayRequest,
    db: Session = Depends(get_db),
) -> WorkflowRun:
    try:
        replay = WorkflowEngine(db).replay_run(run_id, from_step_id=payload.from_step_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not replay:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return replay


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
