import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from graphlib import CycleError, TopologicalSorter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.planner_agent import PlannedStep, planner_agent
from app.agents.worker_agent import WorkerAgent
from app.models.common import StepStatus, TaskStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository
from app.schemas.memory import VectorWriteRequest
from app.schemas.workflow import WorkflowRun, WorkflowTimelineEvent
from app.services.memory_service import MemoryService
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)


@dataclass
class StepExecutionOutcome:
    success: bool
    output_text: str
    attempts: int
    latency_ms: int
    last_error: str | None
    retried: bool
    used_fallback: bool


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.run_repo = WorkflowRunRepository(db)
        self.memory_service = MemoryService(db)

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

    def _execute_with_retry(self, step: ExecutionStepModel) -> StepExecutionOutcome:
        start = time.perf_counter()
        attempts = 0
        max_attempts = step.max_retries + 1
        last_error: str | None = None
        used_fallback = False
        action = step.action
        worker = WorkerAgent(name=step.worker_name)

        while attempts < max_attempts:
            attempts += 1
            try:
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
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if step.fallback_action and not used_fallback:
                    action = step.fallback_action
                    used_fallback = True
                    continue
                if attempts >= max_attempts:
                    break
                time.sleep(step.backoff_seconds * (2 ** (attempts - 1)))

        latency_ms = int((time.perf_counter() - start) * 1000)
        return StepExecutionOutcome(
            success=False,
            output_text=last_error or "step_failed",
            attempts=attempts,
            latency_ms=latency_ms,
            last_error=last_error,
            retried=attempts > 1,
            used_fallback=used_fallback,
        )

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

            now = datetime.now(UTC)
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
            with ThreadPoolExecutor(max_workers=len(ready_step_ids)) as executor:
                futures = {
                    executor.submit(self._execute_with_retry, step_rows[step_id]): step_id for step_id in ready_step_ids
                }
                for future in as_completed(futures):
                    step_id = futures[future]
                    outcomes[step_id] = future.result()

            for step_id in ready_step_ids:
                step = step_rows[step_id]
                outcome = outcomes[step_id]
                finished_at = datetime.now(UTC)

                if outcome.retried:
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
            self.run_repo.set_run_status(run, WorkflowRunStatus.completed)
            self.task_repo.set_status(task, TaskStatus.completed)
            self._log_event(
                run_id=run.id,
                event_type="workflow_completed",
                message="Workflow execution completed.",
            )

        logger.info("workflow.finished", extra={"run_id": run.id, "task_id": task.id, "trace_id": run.trace_id})
        return WorkflowRun.model_validate(self.run_repo.get_run(run.id))

    def get_run(self, run_id: int) -> WorkflowRun | None:
        run = self.run_repo.get_run(run_id)
        return WorkflowRun.model_validate(run) if run else None

    def get_timeline(self, run_id: int) -> list[WorkflowTimelineEvent]:
        return [WorkflowTimelineEvent.model_validate(row) for row in self.run_repo.list_events(run_id)]
