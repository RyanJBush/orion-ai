from app.agents.planner_agent import planner_agent
from app.models.common import StepStatus, TaskPriority, WorkflowRunStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository


def test_planner_creates_dependency_for_then_prefix():
    steps = planner_agent.decompose(
        "Dependency planning",
        "draft outline. then compute 2 + 3",
    )

    assert len(steps) == 2
    assert steps[1].dependencies == [steps[0].id]
    assert steps[1].action == "math"


def test_planner_assigns_retry_and_fallback_policy_for_flaky_step():
    steps = planner_agent.decompose("Retry policy", "flaky downstream call")

    assert len(steps) == 1
    step = steps[0]
    assert step.action == "flaky"
    assert step.retry_policy.max_retries == 2
    assert step.fallback_action == "echo"
    assert step.fallback_on_errors == ["timeout", "runtime"]


def test_workflow_metrics_aggregates_retries_latency_and_tool_reliability(client, db_session):
    task_repo = TaskRepository(db_session)
    run_repo = WorkflowRunRepository(db_session)

    completed_task = task_repo.create("Metrics completed", "completed run", TaskPriority.normal)
    completed_run = run_repo.create_run("default", completed_task.id, "trace-completed")
    run_repo.set_run_status(completed_run, WorkflowRunStatus.completed)
    run_repo.add_step(
        run_id=completed_run.id,
        step_id="step-1",
        step_order=1,
        worker_name="worker-general",
        action="echo",
        input_text="ok",
        dependencies=[],
        expected_output="ok",
        completion_criteria="done",
        max_retries=1,
        backoff_seconds=0.01,
        timeout_seconds=1.0,
        fallback_action=None,
        fallback_on_errors=[],
        status=StepStatus.completed,
        output_text="ok",
    )

    failed_task = task_repo.create("Metrics failed", "failed run", TaskPriority.normal)
    failed_run = run_repo.create_run("default", failed_task.id, "trace-failed")
    run_repo.set_run_status(failed_run, WorkflowRunStatus.failed)
    run_repo.add_step(
        run_id=failed_run.id,
        step_id="step-2",
        step_order=1,
        worker_name="worker-general",
        action="flaky",
        input_text="retry me",
        dependencies=[],
        expected_output="ok",
        completion_criteria="done",
        max_retries=2,
        backoff_seconds=0.01,
        timeout_seconds=1.0,
        fallback_action="echo",
        fallback_on_errors=["runtime"],
        status=StepStatus.failed,
        output_text="failed",
    )

    run_step_1 = next(step for step in completed_run.steps if step.step_id == "step-1")
    run_repo.update_step(
        run_step_1,
        status=StepStatus.completed,
        output_text="ok",
        attempt_count=1,
        latency_ms=100,
        last_error=None,
        started_at=run_step_1.started_at,
        finished_at=run_step_1.finished_at,
    )

    run_step_2 = next(step for step in failed_run.steps if step.step_id == "step-2")
    run_repo.update_step(
        run_step_2,
        status=StepStatus.failed,
        output_text="failed",
        attempt_count=3,
        latency_ms=300,
        last_error="boom",
        started_at=run_step_2.started_at,
        finished_at=run_step_2.finished_at,
    )

    response = client.get("/api/v1/workflows/metrics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["total_runs"] == 2
    assert payload["completion_rate"] == 0.5
    assert payload["retry_rate"] == 0.5
    assert payload["avg_step_latency_ms"] == 200.0
    assert payload["run_status_counts"]["completed"] == 1
    assert payload["run_status_counts"]["failed"] == 1

    reliability = {row["tool"]: row for row in payload["tool_reliability"]}
    assert reliability["echo"] == {"tool": "echo", "completed": 1, "failed": 0, "success_rate": 1.0}
    assert reliability["flaky"] == {"tool": "flaky", "completed": 0, "failed": 1, "success_rate": 0.0}
