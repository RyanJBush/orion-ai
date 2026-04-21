def test_usage_quota_limits_task_submission(client):
    set_quota = client.post("/api/v1/usage/quota", json={"actor_id": "quota-user", "max_runs": 1})
    assert set_quota.status_code == 200
    assert set_quota.json()["max_runs"] == 1

    first = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Quota run 1",
            "description": "echo one",
            "workflow_name": "default",
            "actor_id": "quota-user",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Quota run 2",
            "description": "echo two",
            "workflow_name": "default",
            "actor_id": "quota-user",
        },
    )
    assert second.status_code == 429


def test_usage_quota_endpoint_returns_remaining_runs(client):
    client.post("/api/v1/usage/quota", json={"actor_id": "reader", "max_runs": 3})
    quota = client.get("/api/v1/usage/quota/reader")
    assert quota.status_code == 200
    payload = quota.json()
    assert payload["actor_id"] == "reader"
    assert payload["remaining_runs"] <= payload["max_runs"]
