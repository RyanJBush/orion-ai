import pytest

from app.agents.planner_agent import PlannedStep, RetryPolicy
from app.models.common import ApprovalStatus, StepStatus, TaskPriority, WorkflowRunStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository
from app.schemas.approval import ToolApprovalDecision, ToolApprovalRequestCreate
from app.services.approval_service import ToolApprovalService
from app.services.workflow_engine import WorkflowEngine
from app.tools.base import ToolPermissionError


def _make_step(step_id: str, deps: list[str] | None = None) -> PlannedStep:
    return PlannedStep(
        id=step_id,
        order=1,
        owner="worker-general",
        action="echo",
        instruction="test",
        dependencies=deps or [],
        expected_output="x",
        completion_criteria="done",
        retry_policy=RetryPolicy(max_retries=0, backoff_seconds=0.01),
    )


# ---------------------------------------------------------------------------
# _error_code_for_failure_class
# ---------------------------------------------------------------------------


class TestErrorCodeMapping:
    def test_timeout_maps_to_tool_timeout(self):
        assert WorkflowEngine._error_code_for_failure_class("timeout") == "ORION_TOOL_TIMEOUT"

    def test_runtime_maps_to_tool_runtime(self):
        assert WorkflowEngine._error_code_for_failure_class("runtime") == "ORION_TOOL_RUNTIME"

    def test_permission_maps_to_tool_permission(self):
        assert WorkflowEngine._error_code_for_failure_class("permission") == "ORION_TOOL_PERMISSION"

    def test_canceled_maps_to_workflow_canceled(self):
        assert WorkflowEngine._error_code_for_failure_class("canceled") == "ORION_WORKFLOW_CANCELED"

    def test_blocked_maps_to_workflow_blocked(self):
        assert WorkflowEngine._error_code_for_failure_class("blocked") == "ORION_WORKFLOW_BLOCKED"

    def test_unknown_string_falls_back_to_workflow_error(self):
        assert WorkflowEngine._error_code_for_failure_class("something_else") == "ORION_WORKFLOW_ERROR"

    def test_none_defaults_to_runtime_via_or_fallback(self):
        # None is falsy, so `failure_class or "runtime"` resolves to "runtime"
        assert WorkflowEngine._error_code_for_failure_class(None) == "ORION_TOOL_RUNTIME"


# ---------------------------------------------------------------------------
# _format_error
# ---------------------------------------------------------------------------


class TestFormatError:
    def test_none_message_returns_none(self):
        assert WorkflowEngine._format_error(failure_class="timeout", message=None) is None

    def test_empty_message_returns_none(self):
        assert WorkflowEngine._format_error(failure_class="runtime", message="") is None

    def test_valid_message_is_prefixed_with_error_code(self):
        result = WorkflowEngine._format_error(failure_class="timeout", message="timed out after 5s")
        assert result == "[ORION_TOOL_TIMEOUT] timed out after 5s"

    def test_permission_failure_formats_correctly(self):
        result = WorkflowEngine._format_error(failure_class="permission", message="not allowed")
        assert result == "[ORION_TOOL_PERMISSION] not allowed"


# ---------------------------------------------------------------------------
# _validate_plan
# ---------------------------------------------------------------------------


class TestValidatePlan:
    def test_empty_plan_is_valid(self, db_session):
        WorkflowEngine(db_session)._validate_plan([])

    def test_linear_sequential_plan_is_valid(self, db_session):
        steps = [_make_step("step-1"), _make_step("step-2", ["step-1"])]
        WorkflowEngine(db_session)._validate_plan(steps)

    def test_unknown_dependency_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="unknown dependencies"):
            WorkflowEngine(db_session)._validate_plan([_make_step("step-1", ["step-99"])])

    def test_cyclic_dependency_raises_value_error(self, db_session):
        steps = [_make_step("step-1", ["step-2"]), _make_step("step-2", ["step-1"])]
        with pytest.raises(ValueError, match="cycle detected"):
            WorkflowEngine(db_session)._validate_plan(steps)


# ---------------------------------------------------------------------------
# _ensure_tool_approved
# ---------------------------------------------------------------------------


class TestEnsureToolApproved:
    def test_non_approval_required_tool_passes_silently(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-no-approval")
        WorkflowEngine(db_session)._ensure_tool_approved(run.id, "step-1", "echo")

    def test_approved_sensitive_tool_passes_silently(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-approved")
        approval_service = ToolApprovalService(db_session)
        req = approval_service.request(
            ToolApprovalRequestCreate(
                run_id=run.id,
                step_id="step-1",
                tool_name="sensitive_echo",
                requested_by="operator",
                reason="automated test",
            )
        )
        approval_service.decide(req.id, ToolApprovalDecision(status=ApprovalStatus.approved, reviewed_by="admin"))
        WorkflowEngine(db_session)._ensure_tool_approved(run.id, "step-1", "sensitive_echo")

    def test_unapproved_sensitive_tool_raises_permission_error(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-unapproved")
        with pytest.raises(ToolPermissionError):
            WorkflowEngine(db_session)._ensure_tool_approved(run.id, "step-1", "sensitive_echo")


# ---------------------------------------------------------------------------
# execute_task — task not found
# ---------------------------------------------------------------------------


def test_execute_task_raises_value_error_for_nonexistent_task(db_session):
    with pytest.raises(ValueError, match="Task -1 not found"):
        WorkflowEngine(db_session).execute_task(-1, workflow_name="default")


# ---------------------------------------------------------------------------
# pause_run — edge cases that return None or set paused from pending
# ---------------------------------------------------------------------------


class TestPauseRunEdgeCases:
    def test_returns_none_for_nonexistent_run(self, db_session):
        assert WorkflowEngine(db_session).pause_run(-1) is None

    def test_returns_none_for_completed_run(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-pause-completed")
        run_repo.set_run_status(run, WorkflowRunStatus.completed)
        assert WorkflowEngine(db_session).pause_run(run.id) is None

    def test_returns_none_for_failed_run(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-pause-failed")
        run_repo.set_run_status(run, WorkflowRunStatus.failed)
        assert WorkflowEngine(db_session).pause_run(run.id) is None

    def test_pending_run_is_immediately_set_to_paused(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-pause-pending")
        result = WorkflowEngine(db_session).pause_run(run.id)
        assert result is not None
        assert result.status == WorkflowRunStatus.paused


# ---------------------------------------------------------------------------
# resume_run — edge cases
# ---------------------------------------------------------------------------


class TestResumeRunEdgeCases:
    def test_returns_none_for_nonexistent_run(self, db_session):
        assert WorkflowEngine(db_session).resume_run(-1) is None

    def test_returns_none_for_non_paused_run(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-resume-completed")
        run_repo.set_run_status(run, WorkflowRunStatus.completed)
        assert WorkflowEngine(db_session).resume_run(run.id) is None

    def test_returns_none_when_task_not_found(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-resume-no-task")
        run_repo.set_run_status(run, WorkflowRunStatus.paused)
        engine = WorkflowEngine(db_session)
        engine.task_repo.get = lambda tid: None
        assert engine.resume_run(run.id) is None

    def test_paused_step_is_reset_to_pending_and_executed(self, db_session):
        task = TaskRepository(db_session).create("Resume task", "echo resume", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-resume-paused-step")
        run_repo.set_run_status(run, WorkflowRunStatus.paused)
        run_repo.add_step(
            run_id=run.id,
            step_id="step-1",
            step_order=1,
            worker_name="worker-general",
            action="echo",
            input_text="resume payload",
            dependencies=[],
            expected_output="resume payload",
            completion_criteria="done",
            max_retries=0,
            backoff_seconds=0.01,
            timeout_seconds=2.0,
            fallback_action=None,
            fallback_on_errors=[],
            status=StepStatus.paused,
        )
        result = WorkflowEngine(db_session).resume_run(run.id)
        assert result is not None
        assert result.status == WorkflowRunStatus.completed

    def test_blocked_and_retrying_steps_are_reset_to_pending_and_executed(self, db_session):
        task = TaskRepository(db_session).create("Resume blocked", "echo blocked", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-resume-blocked-steps")
        run_repo.set_run_status(run, WorkflowRunStatus.paused)
        run_repo.add_step(
            run_id=run.id,
            step_id="step-1",
            step_order=1,
            worker_name="worker-general",
            action="echo",
            input_text="blocked input",
            dependencies=[],
            expected_output="done",
            completion_criteria="done",
            max_retries=0,
            backoff_seconds=0.01,
            timeout_seconds=2.0,
            fallback_action=None,
            fallback_on_errors=[],
            status=StepStatus.blocked,
        )
        run_repo.add_step(
            run_id=run.id,
            step_id="step-2",
            step_order=2,
            worker_name="worker-general",
            action="echo",
            input_text="retrying input",
            dependencies=[],
            expected_output="done",
            completion_criteria="done",
            max_retries=0,
            backoff_seconds=0.01,
            timeout_seconds=2.0,
            fallback_action=None,
            fallback_on_errors=[],
            status=StepStatus.retrying,
        )
        result = WorkflowEngine(db_session).resume_run(run.id)
        assert result is not None
        assert result.status == WorkflowRunStatus.completed
        completed_steps = {s.step_id for s in result.steps if s.status == StepStatus.completed}
        assert "step-1" in completed_steps
        assert "step-2" in completed_steps


# ---------------------------------------------------------------------------
# cancel_run — edge cases that return None
# ---------------------------------------------------------------------------


class TestCancelRunEdgeCases:
    def test_returns_none_for_nonexistent_run(self, db_session):
        assert WorkflowEngine(db_session).cancel_run(-1) is None

    def test_returns_none_for_completed_run(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-cancel-completed")
        run_repo.set_run_status(run, WorkflowRunStatus.completed)
        assert WorkflowEngine(db_session).cancel_run(run.id) is None

    def test_returns_none_for_already_canceled_run(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run_repo = WorkflowRunRepository(db_session)
        run = run_repo.create_run("default", task.id, "trace-cancel-already-canceled")
        run_repo.set_run_status(run, WorkflowRunStatus.canceled)
        assert WorkflowEngine(db_session).cancel_run(run.id) is None


# ---------------------------------------------------------------------------
# replay_run — edge cases
# ---------------------------------------------------------------------------


class TestReplayRunEdgeCases:
    def test_returns_none_for_nonexistent_run(self, db_session):
        assert WorkflowEngine(db_session).replay_run(-1, from_step_id=None) is None

    def test_returns_none_when_task_not_found(self, db_session):
        task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-replay-no-task")
        engine = WorkflowEngine(db_session)
        engine.task_repo.get = lambda tid: None
        assert engine.replay_run(run.id, from_step_id=None) is None

    def test_empty_step_list_re_executes_task_from_scratch(self, db_session):
        task = TaskRepository(db_session).create("Replay empty", "echo fresh start", TaskPriority.normal)
        run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-replay-empty")
        result = WorkflowEngine(db_session).replay_run(run.id, from_step_id=None)
        assert result is not None
        assert result.status == WorkflowRunStatus.completed

    def test_replay_from_second_step_pre_completes_first_step(self, client):
        resp = client.post(
            "/api/v1/tasks/submit",
            json={
                "title": "Two step replay",
                "description": "echo alpha. then echo beta",
                "workflow_name": "default",
            },
        )
        assert resp.status_code == 200
        original = resp.json()
        assert original["status"] == "completed"

        replay = client.post(
            f"/api/v1/workflows/runs/{original['id']}/replay",
            json={"from_step_id": "step-2"},
        )
        assert replay.status_code == 200
        replay_run = replay.json()
        assert replay_run["id"] != original["id"]
        steps_by_id = {s["step_id"]: s for s in replay_run["steps"]}
        assert steps_by_id["step-1"]["status"] == StepStatus.completed.value
        assert steps_by_id["step-2"]["status"] == StepStatus.completed.value
