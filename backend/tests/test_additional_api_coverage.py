from app.models.common import StepStatus, TaskPriority, WorkflowRunStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository

NONEXISTENT_ID = -1


def test_agents_create_and_list_endpoints(client):
    created = client.post("/api/v1/agents", json={"name": "planner-bot", "role": "planner"})
    assert created.status_code == 200
    payload = created.json()
    assert payload["name"] == "planner-bot"
    assert payload["role"] == "planner"
    assert payload["model"]

    listed = client.get("/api/v1/agents")
    assert listed.status_code == 200
    assert any(row["id"] == payload["id"] for row in listed.json())


def test_tool_health_endpoint(client):
    response = client.get("/api/v1/tools/health")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    assert all(set(row.keys()).issuperset({"tool", "healthy", "status"}) for row in rows)


def test_workflow_create_and_list_endpoints(client):
    created = client.post(
        "/api/v1/workflows",
        json={"name": "coverage-workflow", "description": "workflow created by coverage test"},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["name"] == "coverage-workflow"

    listed = client.get("/api/v1/workflows")
    assert listed.status_code == 200
    assert any(row["id"] == payload["id"] for row in listed.json())


def test_workflow_run_endpoints_return_404_for_missing_runs(client):
    missing_run_id = NONEXISTENT_ID
    run = client.get(f"/api/v1/workflows/runs/{missing_run_id}")
    timeline = client.get(f"/api/v1/workflows/runs/{missing_run_id}/timeline")
    metrics = client.get(f"/api/v1/workflows/runs/{missing_run_id}/metrics")
    insights = client.get(f"/api/v1/workflows/runs/{missing_run_id}/insights")

    for response in (run, timeline, metrics, insights):
        assert response.status_code == 404
        assert response.json()["detail"] == "Workflow run not found"


def test_workflow_template_run_returns_404_for_missing_template(client):
    response = client.post(f"/api/v1/workflows/templates/{NONEXISTENT_ID}/run")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow template not found"


def test_pause_resume_and_cancel_workflow_controls(client, db_session):
    task_repo = TaskRepository(db_session)
    run_repo = WorkflowRunRepository(db_session)

    paused_task = task_repo.create("Paused run task", "Task for testing resume workflow control", TaskPriority.normal)
    paused_run = run_repo.create_run("default", paused_task.id, "trace-paused")
    run_repo.set_run_status(paused_run, WorkflowRunStatus.paused)

    resumed = client.post(f"/api/v1/workflows/runs/{paused_run.id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == WorkflowRunStatus.running.value
    assert resumed.json()["pause_requested"] is False

    pending_task = task_repo.create("Pending run task", "Task for testing pause workflow control", TaskPriority.normal)
    pending_run = run_repo.create_run("default", pending_task.id, "trace-pending")

    paused = client.post(f"/api/v1/workflows/runs/{pending_run.id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == WorkflowRunStatus.paused.value
    assert paused.json()["pause_requested"] is True

    cancellable_task = task_repo.create(
        "Cancellable run task",
        "Task for testing cancel workflow control",
        TaskPriority.normal,
    )
    cancellable_run = run_repo.create_run("default", cancellable_task.id, "trace-cancel")
    run_repo.set_run_status(cancellable_run, WorkflowRunStatus.running)
    run_repo.add_step(
        run_id=cancellable_run.id,
        step_id="step-pending",
        step_order=1,
        worker_name="worker-general",
        action="echo",
        input_text="cancel me",
        dependencies=[],
        expected_output="cancel",
        completion_criteria="done",
        max_retries=0,
        backoff_seconds=0.01,
        timeout_seconds=1.0,
        fallback_action=None,
        fallback_on_errors=[],
        status=StepStatus.pending,
    )
    run_repo.add_step(
        run_id=cancellable_run.id,
        step_id="step-completed",
        step_order=2,
        worker_name="worker-general",
        action="echo",
        input_text="already done",
        dependencies=[],
        expected_output="done",
        completion_criteria="done",
        max_retries=0,
        backoff_seconds=0.01,
        timeout_seconds=1.0,
        fallback_action=None,
        fallback_on_errors=[],
        status=StepStatus.completed,
        output_text="done",
    )

    canceled = client.post(f"/api/v1/workflows/runs/{cancellable_run.id}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == WorkflowRunStatus.canceled.value
    assert canceled.json()["cancel_requested"] is True

    reloaded = client.get(f"/api/v1/workflows/runs/{cancellable_run.id}")
    assert reloaded.status_code == 200
    steps_by_id = {step["step_id"]: step for step in reloaded.json()["steps"]}
    assert steps_by_id["step-pending"]["status"] == StepStatus.canceled.value
    assert steps_by_id["step-completed"]["status"] == StepStatus.completed.value
