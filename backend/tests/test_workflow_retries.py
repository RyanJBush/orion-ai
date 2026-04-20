def test_flaky_step_retries_and_completes_with_fallback(client):
    response = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Handle transient failure",
            "description": "flaky integration call",
            "workflow_name": "default",
        },
    )
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"

    flaky_step = next((step for step in run["steps"] if step["action"] == "flaky"), None)
    assert flaky_step is not None
    assert flaky_step["attempt_count"] >= 2
    assert flaky_step["status"] == "completed"

    timeline = client.get(f"/api/v1/workflows/runs/{run['id']}/timeline")
    assert timeline.status_code == 200
    events = timeline.json()
    assert any(event["event_type"] == "step_retrying" for event in events)
