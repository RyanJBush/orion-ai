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


def test_get_task(client):
    created = client.post("/api/v1/tasks", json={"title": "Task one", "description": "D1"})
    assert created.status_code == 200
    task_id = created.json()["id"]

    fetched = client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id
