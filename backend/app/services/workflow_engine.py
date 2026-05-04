import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.contracts import AgentRequest
from app.agents.planner_agent import PlannedStep, planner_agent
from app.agents.reviewer_agent import reviewer_agent
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

    @staticmethod
    def _error_code_for_failure_class(failure_class: str | None) -> str:
        mapping = {
            "timeout": "ORION_TOOL_TIMEOUT",
            "runtime": "ORION_TOOL_RUNTIME",
            "permission": "ORION_TOOL_PERMISSION",
            "canceled": "ORION_WORKFLOW_CANCELED",
            "blocked": "ORION_WORKFLOW_BLOCKED",
        }
        return mapping.get(failure_class or "runtime", "ORION_WORKFLOW_ERROR")

    @classmethod
    def _format_error(cls, *, failure_class: str | None, message: str | None) -> str | None:
        if not message:
            return None
        return f"[{cls._error_code_for_failure_class(failure_class)}] {message}"

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

    def _pause_or_cancel_if_requested(self, run, task, *, step_rows: dict[str, ExecutionStepModel]) -> bool:
        self.db.refresh(run)
        if run.cancel_requested:
            self.run_repo.set_run_status(run, WorkflowRunStatus.canceled)
            self.task_repo.set_status(task, TaskStatus.failed)
            self._log_event(run_id=run.id, event_type="workflow_canceled", message="Workflow canceled by request.")
            return True
        if run.pause_requested and run.status != WorkflowRunStatus.paused:
            self.run_repo.set_run_status(run, WorkflowRunStatus.paused)
            for step in step_rows.values():
                if step.status == StepStatus.pending:
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.paused,
                        output_text=step.output_text,
                        attempt_count=step.attempt_count,
                        latency_ms=step.latency_ms,
                        last_error=step.last_error,
                        started_at=step.started_at,
                        finished_at=step.finished_at,
                    )
            self._log_event(run_id=run.id, event_type="workflow_paused", message="Workflow paused by request.")
        return False

    def _execute_run_loop(
        self,
        *,
        task,
        run,
        step_rows: dict[str, ExecutionStepModel],
        completed: set[str] | None = None,
    ) -> WorkflowRun:
        completed_steps = set(completed or set())
        failed = False

        while len(completed_steps) < len(step_rows):
            if self._pause_or_cancel_if_requested(run, task, step_rows=step_rows):
                return WorkflowRun.model_validate(self.run_repo.get_run(run.id))
            if run.status == WorkflowRunStatus.paused:
                break

            ready_step_ids = [
                step_id
                for step_id, step in step_rows.items()
                if step.status in {StepStatus.pending, StepStatus.paused}
                and set(step.dependencies).issubset(completed_steps)
            ]
            if not ready_step_ids:
                self.run_repo.set_run_status(run, WorkflowRunStatus.blocked)
                self._log_event(
                    run_id=run.id,
                    event_type="workflow_blocked",
                    message="No runnable steps available; unresolved dependencies.",
                    metadata={"error_code": self._error_code_for_failure_class("blocked")},
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
                        last_error=self._format_error(failure_class=outcome.failure_class, message=outcome.last_error),
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
                    review = reviewer_agent.review(
                        request=AgentRequest(
                            workflow_id=str(run.id),
                            step_id=step.step_id,
                            goal=step.input_text,
                            context={
                                "candidate_output": outcome.output_text,
                                "criteria": [step.completion_criteria, step.expected_output],
                            },
                        )
                    )
                    review_output = review.output
                    self._log_event(
                        run_id=run.id,
                        step_pk_id=step.id,
                        event_type="step_reviewed",
                        message=f"Step {step.step_id} reviewed by reviewer agent.",
                        metadata={
                            "approved": review_output.get("approved", False),
                            "score": review_output.get("score", 0),
                            "reasoning": review.reasoning_trace.summary,
                        },
                    )
                    if not review_output.get("approved", False):
                        outcome.success = False
                        outcome.last_error = "reviewer rejected step output"
                        outcome.failure_class = "runtime"

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
                    completed_steps.add(step_id)
                    self.memory_service.write_vector(
                        payload=VectorWriteRequest(
                            namespace=f"task:{task.id}",
                            text=f"{step.input_text} -> {outcome.output_text}",
                            scope=MemoryScope.short_term,
                            memory_type=MemoryType.tool_result,
                            source_ref=f"run:{run.id}:step:{step.step_id}",
                        )
                    )
                    self.memory_service.write_basic(
                        payload=MemoryWriteRequest(
                            namespace=f"task:{task.id}",
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
                            "tool": step.action,
                            "worker": step.worker_name,
                        },
                    )
                else:
                    error_code = self._error_code_for_failure_class(outcome.failure_class)
                    self.run_repo.update_step(
                        step,
                        status=StepStatus.failed,
                        output_text=outcome.output_text,
                        attempt_count=outcome.attempts,
                        latency_ms=outcome.latency_ms,
                        last_error=self._format_error(failure_class=outcome.failure_class, message=outcome.last_error),
                        started_at=step.started_at,
                        finished_at=finished_at,
                    )
                    self._log_event(
                        run_id=run.id,
                        step_pk_id=step.id,
                        event_type="step_failed",
                        message=f"Step {step.step_id} failed.",
                        metadata={
                            "attempts": outcome.attempts,
                            "error": outcome.last_error,
                            "error_code": error_code,
                            "failure_class": outcome.failure_class,
                            "tool": step.action,
                            "worker": step.worker_name,
                        },
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
                            namespace=f"task:{task.id}",
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

        return self._execute_run_loop(task=task, run=run, step_rows=step_rows)

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
        task = self.task_repo.get(run.task_id)
        if task is None:
            return None

        self.run_repo.clear_pause_request(run)
        self.run_repo.set_run_status(run, WorkflowRunStatus.running)
        self.task_repo.set_status(task, TaskStatus.running)
        self._log_event(run_id=run.id, event_type="workflow_resumed", message="Workflow resumed.")

        step_rows: dict[str, ExecutionStepModel] = {}
        completed: set[str] = set()
        for step in sorted(run.steps, key=lambda row: row.step_order):
            if step.status == StepStatus.completed:
                completed.add(step.step_id)
            elif step.status in {StepStatus.paused, StepStatus.blocked, StepStatus.retrying}:
                step = self.run_repo.update_step(
                    step,
                    status=StepStatus.pending,
                    output_text=step.output_text,
                    attempt_count=step.attempt_count,
                    latency_ms=step.latency_ms,
                    last_error=step.last_error,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                )
            step_rows[step.step_id] = step

        return self._execute_run_loop(task=task, run=run, step_rows=step_rows, completed=completed)

    def replay_run(self, run_id: int, from_step_id: str | None = None) -> WorkflowRun | None:
        source_run = self.run_repo.get_run(run_id)
        if source_run is None:
            return None
        task = self.task_repo.get(source_run.task_id)
        if task is None:
            return None

        ordered_steps = sorted(source_run.steps, key=lambda row: row.step_order)
        if not ordered_steps:
            return self.execute_task(task.id, workflow_name=source_run.workflow_name)

        valid_step_ids = {step.step_id for step in ordered_steps}
        if from_step_id is not None and from_step_id not in valid_step_ids:
            raise ValueError(f"from_step_id '{from_step_id}' not found in run {run_id}")

        trace_id = f"trace-{uuid4().hex[:16]}"
        self.task_repo.set_status(task, TaskStatus.running)
        replay_run = self.run_repo.create_run(workflow_name=source_run.workflow_name, task_id=task.id, trace_id=trace_id)
        self.run_repo.set_run_status(replay_run, WorkflowRunStatus.running)
        self._log_event(
            run_id=replay_run.id,
            event_type="workflow_replayed",
            message=f"Replay started from run {source_run.id}.",
            metadata={"source_run_id": source_run.id, "from_step_id": from_step_id},
        )

        step_rows: dict[str, ExecutionStepModel] = {}
        completed: set[str] = set()
        replay_started = from_step_id is None
        for source_step in ordered_steps:
            if source_step.step_id == from_step_id:
                replay_started = True

            status = StepStatus.pending
            output_text = ""
            attempt_count = 0
            latency_ms = None
            started_at = None
            finished_at = None
            if not replay_started:
                status = StepStatus.completed
                output_text = source_step.output_text
                attempt_count = max(source_step.attempt_count, 1)
                latency_ms = source_step.latency_ms
                started_at = source_step.started_at
                finished_at = source_step.finished_at
                completed.add(source_step.step_id)

            step = self.run_repo.add_step(
                run_id=replay_run.id,
                step_id=source_step.step_id,
                step_order=source_step.step_order,
                worker_name=source_step.worker_name,
                action=source_step.action,
                input_text=source_step.input_text,
                dependencies=source_step.dependencies,
                expected_output=source_step.expected_output,
                completion_criteria=source_step.completion_criteria,
                max_retries=source_step.max_retries,
                backoff_seconds=source_step.backoff_seconds,
                timeout_seconds=source_step.timeout_seconds,
                fallback_action=source_step.fallback_action,
                fallback_on_errors=source_step.fallback_on_errors,
                status=status,
                output_text=output_text,
            )
            if status == StepStatus.completed:
                step = self.run_repo.update_step(
                    step,
                    status=StepStatus.completed,
                    output_text=output_text,
                    attempt_count=attempt_count,
                    latency_ms=latency_ms,
                    last_error=None,
                    started_at=started_at,
                    finished_at=finished_at,
                )
            step_rows[step.step_id] = step

        return self._execute_run_loop(task=task, run=replay_run, step_rows=step_rows, completed=completed)

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
            if step.status in {StepStatus.pending, StepStatus.running, StepStatus.retrying, StepStatus.blocked, StepStatus.paused}:
                self.run_repo.update_step(
                    step,
                    status=StepStatus.canceled,
                    output_text=step.output_text,
                    attempt_count=step.attempt_count,
                    latency_ms=step.latency_ms,
                    last_error=self._format_error(failure_class="canceled", message=step.last_error),
                    started_at=step.started_at,
                    finished_at=datetime.now(timezone.utc),
                )
        self._log_event(run_id=run.id, event_type="workflow_canceled", message="Workflow canceled by request.")
        return WorkflowRun.model_validate(self.run_repo.get_run(run_id))
