def test_submit_task_creates_run(client):
    response = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Prepare report",
            "description": "collect metrics. calculate 2 + 3",
            "workflow_name": "default",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["steps"]) >= 2
    assert {step["action"] for step in data["steps"]} >= {"echo", "math"}
    assert data["trace_id"].startswith("trace-")

    timeline = client.get(f"/api/v1/workflows/runs/{data['id']}/timeline")
    assert timeline.status_code == 200
    assert any(event["event_type"] == "workflow_completed" for event in timeline.json())

    metrics = client.get("/api/v1/workflows/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["total_runs"] >= 1

    insights = client.get(f"/api/v1/workflows/runs/{data['id']}/insights")
    assert insights.status_code == 200
    insight_payload = insights.json()
    assert insight_payload["run_id"] == data["id"]
    assert insight_payload["quality_score"] >= 0
    assert len(insight_payload["suggested_actions"]) >= 1

    memory_summary = client.get(f"/api/v1/memory/summary/task:{data['task_id']}")
    assert memory_summary.status_code == 200
    summary_payload = memory_summary.json()
    assert summary_payload["by_type"]["prior_output"] >= 1


def test_get_task(client):
    created = client.post("/api/v1/tasks", json={"title": "Task one", "description": "D1"})
    assert created.status_code == 200
    task_id = created.json()["id"]

    fetched = client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id


def test_workflow_run_metrics_endpoint(client):
    response = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Resilient workflow",
            "description": "flaky downstream call. then summarize response",
            "workflow_name": "default",
        },
    )
    assert response.status_code == 200
    run_id = response.json()["id"]

    metrics = client.get(f"/api/v1/workflows/runs/{run_id}/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["run_id"] == run_id
    assert payload["total_steps"] >= 1
    assert payload["retried_steps"] >= 1


def test_dispatch_next_queued_task_respects_priority(client):
    low = client.post("/api/v1/tasks/enqueue", json={"title": "Low", "description": "echo this", "priority": "low"})
    urgent = client.post(
        "/api/v1/tasks/enqueue", json={"title": "Urgent", "description": "echo now", "priority": "urgent"}
    )
    assert low.status_code == 200
    assert urgent.status_code == 200

    dispatched = client.post("/api/v1/tasks/dispatch-next", json={"workflow_name": "default"})
    assert dispatched.status_code == 200
    assert dispatched.json()["task_id"] == urgent.json()["id"]


def test_workflow_control_endpoints(client):
    submitted = client.post(
        "/api/v1/tasks/submit",
        json={"title": "Cancelable run", "description": "echo first", "workflow_name": "default"},
    )
    assert submitted.status_code == 200
    run_id = submitted.json()["id"]

    pause = client.post(f"/api/v1/workflows/runs/{run_id}/pause")
    assert pause.status_code == 409

    cancel = client.post(f"/api/v1/workflows/runs/{run_id}/cancel")
    assert cancel.status_code == 409


def test_workflow_template_create_list_and_run(client):
    created = client.post(
        "/api/v1/workflows/templates",
        json={
            "name": "demo-report-template",
            "description": "Demo scenario",
            "task_title": "Run demo report",
            "task_description": "collect metrics. calculate 4 + 5",
            "workflow_name": "default",
            "tags": ["demo", "report"],
            "is_demo": True,
        },
    )
    assert created.status_code == 200
    template_id = created.json()["id"]

    listed = client.get("/api/v1/workflows/templates")
    assert listed.status_code == 200
    assert any(row["id"] == template_id for row in listed.json())

    run = client.post(f"/api/v1/workflows/templates/{template_id}/run")
    assert run.status_code == 200
    assert run.json()["status"] in {"completed", "failed"}


def test_workflow_replay_from_failed_step(client):
    initial = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Replay scenario",
            "description": "please run sensitive operation requiring approval",
            "workflow_name": "default",
        },
    )
    assert initial.status_code == 200
    initial_run = initial.json()
    assert initial_run["status"] == "failed"
    initial_timeline = client.get(f"/api/v1/workflows/runs/{initial_run['id']}/timeline")
    assert initial_timeline.status_code == 200
    failed_event = next(
        (event for event in initial_timeline.json() if event["event_type"] == "step_failed"),
        None,
    )
    assert failed_event is not None
    event_metadata = failed_event.get("metadata") or failed_event.get("event_metadata") or {}
    assert event_metadata["error_code"] == "ORION_TOOL_PERMISSION"

    replay = client.post(
        f"/api/v1/workflows/runs/{initial_run['id']}/replay",
        json={"from_step_id": "step-1"},
    )
    assert replay.status_code == 200
    replay_run = replay.json()
    assert replay_run["id"] != initial_run["id"]
    assert replay_run["task_id"] == initial_run["task_id"]
    assert replay_run["status"] == "failed"

    timeline = client.get(f"/api/v1/workflows/runs/{replay_run['id']}/timeline")
    assert timeline.status_code == 200
    events = timeline.json()
    replay_event = next((event for event in events if event["event_type"] == "workflow_replayed"), None)
    assert replay_event is not None
    replay_metadata = replay_event.get("metadata") or replay_event.get("event_metadata") or {}
    assert replay_metadata["source_run_id"] == initial_run["id"]


def test_workflow_replay_rejects_unknown_step(client):
    initial = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Replay validation",
            "description": "echo one. then echo two",
            "workflow_name": "default",
        },
    )
    assert initial.status_code == 200
    run_id = initial.json()["id"]

    replay = client.post(
        f"/api/v1/workflows/runs/{run_id}/replay",
        json={"from_step_id": "step-999"},
    )
    assert replay.status_code == 422
    assert "from_step_id" in replay.json()["detail"]
