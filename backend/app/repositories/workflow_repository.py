from sqlalchemy.orm import Session, joinedload

from app.models.common import StepStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel, WorkflowRunModel, WorkflowTimelineEventModel


class WorkflowRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(self, workflow_name: str, task_id: int, trace_id: str) -> WorkflowRunModel:
        run = WorkflowRunModel(
            workflow_name=workflow_name,
            task_id=task_id,
            trace_id=trace_id,
            status=WorkflowRunStatus.pending,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def set_run_status(self, run: WorkflowRunModel, status: WorkflowRunStatus) -> WorkflowRunModel:
        run.status = status
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_step(
        self,
        run_id: int,
        step_id: str,
        step_order: int,
        worker_name: str,
        action: str,
        input_text: str,
        dependencies: list[str],
        expected_output: str,
        completion_criteria: str,
        max_retries: int,
        backoff_seconds: float,
        timeout_seconds: float,
        fallback_action: str | None,
        fallback_on_errors: list[str],
        status: StepStatus = StepStatus.pending,
        output_text: str = "",
    ) -> ExecutionStepModel:
        step = ExecutionStepModel(
            run_id=run_id,
            step_id=step_id,
            step_order=step_order,
            worker_name=worker_name,
            action=action,
            input_text=input_text,
            dependencies=dependencies,
            expected_output=expected_output,
            completion_criteria=completion_criteria,
            output_text=output_text,
            status=status,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            timeout_seconds=timeout_seconds,
            fallback_action=fallback_action,
            fallback_on_errors=fallback_on_errors,
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def update_step(
        self,
        step: ExecutionStepModel,
        *,
        status: StepStatus,
        output_text: str,
        attempt_count: int,
        latency_ms: int | None,
        last_error: str | None,
        started_at,
        finished_at,
    ) -> ExecutionStepModel:
        step.status = status
        step.output_text = output_text
        step.attempt_count = attempt_count
        step.latency_ms = latency_ms
        step.last_error = last_error
        step.started_at = started_at
        step.finished_at = finished_at
        self.db.commit()
        self.db.refresh(step)
        return step

    def add_event(
        self,
        *,
        run_id: int,
        event_type: str,
        message: str,
        metadata: dict | None = None,
        step_pk_id: int | None = None,
    ) -> WorkflowTimelineEventModel:
        event = WorkflowTimelineEventModel(
            run_id=run_id,
            step_id=step_pk_id,
            event_type=event_type,
            message=message,
            event_metadata=metadata or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_events(self, run_id: int) -> list[WorkflowTimelineEventModel]:
        return (
            self.db.query(WorkflowTimelineEventModel)
            .filter(WorkflowTimelineEventModel.run_id == run_id)
            .order_by(WorkflowTimelineEventModel.created_at.asc(), WorkflowTimelineEventModel.id.asc())
            .all()
        )

    def get_run(self, run_id: int) -> WorkflowRunModel | None:
        return (
            self.db.query(WorkflowRunModel)
            .options(
                joinedload(WorkflowRunModel.steps),
                joinedload(WorkflowRunModel.timeline_events),
            )
            .filter(WorkflowRunModel.id == run_id)
            .first()
        )

    def request_pause(self, run: WorkflowRunModel) -> WorkflowRunModel:
        run.pause_requested = True
        self.db.commit()
        self.db.refresh(run)
        return run

    def clear_pause_request(self, run: WorkflowRunModel) -> WorkflowRunModel:
        run.pause_requested = False
        self.db.commit()
        self.db.refresh(run)
        return run

    def request_cancel(self, run: WorkflowRunModel) -> WorkflowRunModel:
        run.cancel_requested = True
        self.db.commit()
        self.db.refresh(run)
        return run
