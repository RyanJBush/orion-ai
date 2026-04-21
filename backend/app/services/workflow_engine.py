import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.planner_agent import PlannedStep, planner_agent
from app.agents.worker_agent import WorkerAgent
from app.models.common import MemoryScope, MemoryType, StepStatus, TaskStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository
from app.schemas.audit import AuditLogCreate
from app.schemas.memory import MemoryWriteRequest, VectorWriteRequest
from app.schemas.workflow import WorkflowRun, WorkflowTimelineEvent
from app.services.approval_service import ToolApprovalService
from app.services.audit_service import AuditService
from app.services.memory_service import MemoryService
from app.tools.base import ToolPermissionError, ToolRuntimeError, ToolTimeoutError
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)
MAX_BACKOFF_SECONDS = 1.0
MAX_PARALLEL_STEPS = 8


@dataclass
class StepExecutionOutcome:
    success: bool
    output_text: str
    attempts: int
    latency_ms: int
    last_error: str | None
    retried: bool
    used_fallback: bool
    failure_class: str | None = None


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.run_repo = WorkflowRunRepository(db)
        self.memory_service = MemoryService(db)
        self.approval_service = ToolApprovalService(db)
        self.audit_service = AuditService(db)

    def _ensure_tool_approved(self, run_id: int, step_id: str, action: str) -> None:
        schema = tool_registry.get_schema(action)
        if not schema.requires_approval:
            return
        if self.approval_service.has_approval(run_id=run_id, step_id=step_id, tool_name=action):
            return
        raise ToolPermissionError(
            f"tool '{action}' requires approval. Create approval at /api/v1/approvals for run={run_id}, step={step_id}"
        )

    def _validate_plan(self, steps: list[PlannedStep]) -> None:
        known_ids = {step.id for step in steps}
        graph: dict[str, set[str]] = {}
        for step in steps:
            unknown_dependencies = set(step.dependencies) - known_ids
            if unknown_dependencies:
                raise ValueError(f"Plan validation failed for {step.id}: unknown dependencies {unknown_dependencies}")
            graph[step.id] = set(step.dependencies)
        try:
            sorter = TopologicalSorter(graph)
            _ = tuple(sorter.static_order())
        except CycleError as exc:
            raise ValueError("Plan validation failed: cycle detected in dependencies") from exc

    def _log_event(
        self,
        *,
        run_id: int,
        event_type: str,
        message: str,
        metadata: dict | None = None,
        step_pk_id: int | None = None,
    ) -> None:
        self.run_repo.add_event(
            run_id=run_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
            step_pk_id=step_pk_id,
        )
        self.audit_service.write(
            payload=AuditLogCreate(
                workspace_id="default",
                actor_id="system",
                action=event_type,
                resource_type="workflow_run",
                resource_id=str(run_id),
                details=metadata or {},
                summary=message,
            )
        )

    def _execute_with_retry(self, run, step: ExecutionStepModel) -> StepExecutionOutcome:
        start = time.perf_counter()
        attempts = 0
        max_attempts = step.max_retries + 1
        last_error: str | None = None
        failure_class: str | None = None
        used_fallback = False
        action = step.action
        worker = WorkerAgent(name=step.worker_name)

        while attempts < max_attempts:
            self.db.refresh(run)
            if run.cancel_requested:
                latency_ms = int((time.perf_counter() - start) * 1000)
                return StepExecutionOutcome(
                    success=False,
                    output_text="workflow_canceled",
                    attempts=attempts,
                    latency_ms=latency_ms,
                    last_error="workflow_canceled",
                    retried=attempts > 1,
                    used_fallback=used_fallback,
                    failure_class="canceled",
                )
            attempts += 1
            try:
                self._ensure_tool_approved(run.id, step.step_id, action)
                result = worker.execute(action=action, instruction=step.input_text, timeout_seconds=step.timeout_seconds)
                latency_ms = int((time.perf_counter() - start) * 1000)
                return StepExecutionOutcome(
                    success=True,
                    output_text=result.output,
                    attempts=attempts,
                    latency_ms=latency_ms,
                    last_error=None,
                    retried=attempts > 1,
                    used_fallback=used_fallback,
                )
            except (ToolTimeoutError, ToolRuntimeError, KeyError) as exc:
                last_error = str(exc)
                failure_class = "timeout" if isinstance(exc, ToolTimeoutError) else "runtime"
                can_fallback = not step.fallback_on_errors or failure_class in step.fallback_on_errors
                if step.fallback_action and not used_fallback and can_fallback:
                    action = step.fallback_action
                    used_fallback = True
                    continue
                if attempts >= max_attempts:
                    break
                backoff_delay = min(step.backoff_seconds * (2 ** (attempts - 1)), MAX_BACKOFF_SECONDS)
                time.sleep(backoff_delay)
            except ToolPermissionError as exc:
                last_error = str(exc)
                failure_class = "permission"
                break

        latency_ms = int((time.perf_counter() - start) * 1000)
        return StepExecutionOutcome(
            success=False,
            output_text=last_error or "step_failed",
            attempts=attempts,
            latency_ms=latency_ms,
            last_error=last_error,
            retried=attempts > 1,
            used_fallback=used_fallback,
            failure_class=failure_class or "runtime",
        )

    def _pause_or_cancel_if_requested(self, run, task) -> bool:
        self.db.refresh(run)
        if run.cancel_requested:
            self.run_repo.set_run_status(run, WorkflowRunStatus.canceled)
            self.task_repo.set_status(task, TaskStatus.failed)
            self._log_event(run_id=run.id, event_type="workflow_canceled", message="Workflow canceled by request.")
            return True
        if run.pause_requested and run.status != WorkflowRunStatus.paused:
            self.run_repo.set_run_status(run, WorkflowRunStatus.paused)
            self._log_event(run_id=run.id, event_type="workflow_paused", message="Workflow paused by request.")
        return False

    def execute_task(self, task_id: int, workflow_name: str = "default") -> WorkflowRun:
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        trace_id = f"trace-{uuid4().hex[:16]}"
        self.task_repo.set_status(task, TaskStatus.planning)
        run = self.run_repo.create_run(workflow_name=workflow_name, task_id=task_id, trace_id=trace_id)
        self._log_event(
            run_id=run.id,
            event_type="workflow_pending",
            message="Workflow run created and queued for planning.",
            metadata={"trace_id": run.trace_id, "task_id": task.id},
        )

        plan = planner_agent.decompose(task.title, task.description)
        self._validate_plan(plan)
        self.task_repo.set_status(task, TaskStatus.running)
        self.run_repo.set_run_status(run, WorkflowRunStatus.running)
        self._log_event(
            run_id=run.id,
            event_type="workflow_running",
            message="Workflow execution started.",
            metadata={"step_count": len(plan)},
        )

        step_rows: dict[str, ExecutionStepModel] = {}
        for planned_step in plan:
            schema = tool_registry.get_schema(planned_step.action)
            step = self.run_repo.add_step(
                run_id=run.id,
                step_id=planned_step.id,
                step_order=planned_step.order,
                worker_name=planned_step.owner,
                action=planned_step.action,
                input_text=planned_step.instruction,
                dependencies=planned_step.dependencies,
                expected_output=planned_step.expected_output,
                completion_criteria=planned_step.completion_criteria,
                max_retries=planned_step.retry_policy.max_retries,
                backoff_seconds=planned_step.retry_policy.backoff_seconds,
                timeout_seconds=schema.timeout_seconds,
                fallback_action=planned_step.fallback_action,
                fallback_on_errors=planned_step.fallback_on_errors or [],
                status=StepStatus.pending,
            )
            step_rows[planned_step.id] = step
            self._log_event(
                run_id=run.id,
                step_pk_id=step.id,
                event_type="step_pending",
                message=f"Step {planned_step.id} queued.",
                metadata={"dependencies": planned_step.dependencies},
            )

        completed: set[str] = set()
        failed = False

        while len(completed) < len(step_rows):
            if self._pause_or_cancel_if_requested(run, task):
                return WorkflowRun.model_validate(self.run_repo.get_run(run.id))
            if run.status == WorkflowRunStatus.paused:
                break
            ready_step_ids = [
                step_id
                for step_id, step in step_rows.items()
                if step.status == StepStatus.pending and set(step.dependencies).issubset(completed)
            ]
            if not ready_step_ids:
                self.run_repo.set_run_status(run, WorkflowRunStatus.blocked)
                self._log_event(
                    run_id=run.id,
                    event_type="workflow_blocked",
                    message="No runnable steps available; unresolved dependencies.",
                )
                failed = True
                break

            now = datetime.now(timezone.utc)
            for step_id in ready_step_ids:
                step = step_rows[step_id]
                step.status = StepStatus.running
                step.started_at = now
                self.db.commit()
                self.db.refresh(step)
                self._log_event(
                    run_id=run.id,
                    step_pk_id=step.id,
                    event_type="step_running",
                    message=f"Step {step.step_id} started.",
                )

            outcomes: dict[str, StepExecutionOutcome] = {}
            with ThreadPoolExecutor(max_workers=min(len(ready_step_ids), MAX_PARALLEL_STEPS)) as executor:
                futures = {
                    executor.submit(self._execute_with_retry, run, step_rows[step_id]): step_id for step_id in ready_step_ids
                }
                for future in as_completed(futures):
                    step_id = futures[future]
                    outcomes[step_id] = future.result()

            for step_id in ready_step_ids:
                step = step_rows[step_id]
                outcome = outcomes[step_id]
                finished_at = datetime.now(timezone.utc)

                if outcome.failure_class == "canceled":
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.canceled,
                        output_text=outcome.output_text,
                        attempt_count=outcome.attempts,
                        latency_ms=outcome.latency_ms,
                        last_error=outcome.last_error,
                        started_at=step.started_at,
                        finished_at=finished_at,
                    )
                    self.run_repo.set_run_status(run, WorkflowRunStatus.canceled)
                    self.task_repo.set_status(task, TaskStatus.failed)
                    self._log_event(run_id=run.id, step_pk_id=step.id, event_type="step_canceled", message="Step canceled.")
                    return WorkflowRun.model_validate(self.run_repo.get_run(run.id))

                if outcome.retried:
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.retrying,
                        output_text=step.output_text,
                        attempt_count=outcome.attempts,
                        latency_ms=None,
                        last_error=None,
                        started_at=step.started_at,
                        finished_at=None,
                    )
                    self.run_repo.set_run_status(run, WorkflowRunStatus.retrying)
                    self._log_event(
                        run_id=run.id,
                        step_pk_id=step.id,
                        event_type="step_retrying",
                        message=f"Step {step.step_id} required retries.",
                        metadata={"attempts": outcome.attempts},
                    )
                    self.run_repo.set_run_status(run, WorkflowRunStatus.running)

                if outcome.success:
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.completed,
                        output_text=outcome.output_text,
                        attempt_count=outcome.attempts,
                        latency_ms=outcome.latency_ms,
                        last_error=None,
                        started_at=step.started_at,
                        finished_at=finished_at,
                    )
                    completed.add(step_id)
                    self.memory_service.write_vector(
                        payload=VectorWriteRequest(
                            namespace=f"task:{task_id}",
                            text=f"{step.input_text} -> {outcome.output_text}",
                            scope=MemoryScope.short_term,
                            memory_type=MemoryType.tool_result,
                            source_ref=f"run:{run.id}:step:{step.step_id}",
                        )
                    )
                    self.memory_service.write_basic(
                        payload=MemoryWriteRequest(
                            namespace=f"task:{task_id}",
                            key=f"{run.id}:{step.step_id}",
                            text=outcome.output_text,
                            scope=MemoryScope.short_term,
                            memory_type=MemoryType.tool_result,
                            source_ref=f"trace:{run.trace_id}",
                            metadata={"step_id": step.step_id, "action": step.action},
                        )
                    )
                    self._log_event(
                        run_id=run.id,
                        step_pk_id=step.id,
                        event_type="step_completed",
                        message=f"Step {step.step_id} completed.",
                        metadata={
                            "attempts": outcome.attempts,
                            "latency_ms": outcome.latency_ms,
                            "used_fallback": outcome.used_fallback,
                        },
                    )
                else:
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.failed,
                        output_text=outcome.output_text,
                        attempt_count=outcome.attempts,
                        latency_ms=outcome.latency_ms,
                        last_error=outcome.last_error,
                        started_at=step.started_at,
                        finished_at=finished_at,
                    )
                    self._log_event(
                        run_id=run.id,
                        step_pk_id=step.id,
                        event_type="step_failed",
                        message=f"Step {step.step_id} failed.",
                        metadata={"attempts": outcome.attempts, "error": outcome.last_error},
                    )
                    failed = True
                    break

            if failed:
                break

        if failed:
            self.run_repo.set_run_status(run, WorkflowRunStatus.failed)
            self.task_repo.set_status(task, TaskStatus.failed)
            self._log_event(
                run_id=run.id,
                event_type="workflow_failed",
                message="Workflow execution failed.",
            )
        else:
            if run.status == WorkflowRunStatus.paused:
                self.task_repo.set_status(task, TaskStatus.queued)
            else:
                self.run_repo.set_run_status(run, WorkflowRunStatus.completed)
                self.task_repo.set_status(task, TaskStatus.completed)
                self._log_event(
                    run_id=run.id,
                    event_type="workflow_completed",
                    message="Workflow execution completed.",
                )
                run_snapshot = self.run_repo.get_run(run.id)
                summary_text = "\n".join([f"{s.step_id}: {s.output_text}" for s in run_snapshot.steps if s.output_text])
                if summary_text:
                    self.memory_service.write_basic(
                        payload=MemoryWriteRequest(
                            namespace=f"task:{task_id}",
                            key=f"run-summary:{run.id}",
                            text=summary_text,
                            scope=MemoryScope.long_term,
                            memory_type=MemoryType.prior_output,
                            source_ref=f"trace:{run.trace_id}",
                            metadata={"run_id": run.id},
                        )
                    )

        logger.info("workflow.finished", extra={"run_id": run.id, "task_id": task.id, "trace_id": run.trace_id})
        return WorkflowRun.model_validate(self.run_repo.get_run(run.id))

    def get_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        return WorkflowRun.model_validate(run) if run else None

    def get_timeline(self, run_id: int) -> list[WorkflowTimelineEvent]:
        return [WorkflowTimelineEvent.model_validate(row) for row in self.run_repo.list_events(run_id)]

    def pause_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        if not run or run.status in {WorkflowRunStatus.completed, WorkflowRunStatus.failed, WorkflowRunStatus.canceled}:
            return None
        self.run_repo.request_pause(run)
        if run.status == WorkflowRunStatus.pending:
            self.run_repo.set_run_status(run, WorkflowRunStatus.paused)
        return WorkflowRun.model_validate(self.run_repo.get_run(run_id))

    def resume_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        if not run or run.status != WorkflowRunStatus.paused:
            return None
        self.run_repo.clear_pause_request(run)
        self.run_repo.set_run_status(run, WorkflowRunStatus.running)
        return WorkflowRun.model_validate(self.run_repo.get_run(run_id))

    def cancel_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        if not run or run.status in {WorkflowRunStatus.completed, WorkflowRunStatus.failed, WorkflowRunStatus.canceled}:
            return None
        task = self.task_repo.get(run.task_id)
        self.run_repo.request_cancel(run)
        self.run_repo.set_run_status(run, WorkflowRunStatus.canceled)
        if task:
            self.task_repo.set_status(task, TaskStatus.failed)
        for step in run.steps:
            if step.status in {StepStatus.pending, StepStatus.running, StepStatus.retrying, StepStatus.blocked}:
                self.run_repo.update_step(
                    step,
                    status=StepStatus.canceled,
                    output_text=step.output_text,
                    attempt_count=step.attempt_count,
                    latency_ms=step.latency_ms,
                    last_error=step.last_error,
                    started_at=step.started_at,
                    finished_at=datetime.now(timezone.utc),
                )
        self._log_event(run_id=run.id, event_type="workflow_canceled", message="Workflow canceled by request.")
        return WorkflowRun.model_validate(self.run_repo.get_run(run_id))
