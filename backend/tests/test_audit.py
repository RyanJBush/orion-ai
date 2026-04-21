def test_audit_log_create_and_list(client):
    created = client.post(
        "/api/v1/audit",
        json={
            "workspace_id": "w1",
            "actor_id": "user-1",
            "action": "manual_override",
            "resource_type": "workflow_run",
            "resource_id": "42",
            "details": {"reason": "test"},
            "summary": "card=4111111111111111",
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["workspace_id"] == "w1"
    assert "4111111111111111" not in payload["redacted_summary"]

    listed = client.get("/api/v1/audit", params={"workspace_id": "w1", "limit": 10})
    assert listed.status_code == 200
    rows = listed.json()
    assert any(row["id"] == payload["id"] for row in rows)


def test_workflow_events_are_written_to_audit_log(client):
    run = client.post(
        "/api/v1/tasks/submit",
        json={"title": "Audit flow", "description": "echo hi", "workflow_name": "default"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    logs = client.get("/api/v1/audit", params={"limit": 200})
    assert logs.status_code == 200
    assert any(row["resource_id"] == str(run_id) and row["resource_type"] == "workflow_run" for row in logs.json())
