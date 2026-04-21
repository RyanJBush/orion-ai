from app.models.common import ApprovalStatus


def test_tool_approval_crud_flow(client):
    run_resp = client.post(
        "/api/v1/tasks/submit",
        json={"title": "Baseline run", "description": "echo hello", "workflow_name": "default"},
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    created = client.post(
        "/api/v1/approvals",
        json={
            "run_id": run_id,
            "step_id": "step-99",
            "tool_name": "sensitive_echo",
            "requested_by": "operator-1",
            "reason": "requires human validation",
        },
    )
    assert created.status_code == 200
    approval_id = created.json()["id"]
    assert created.json()["status"] == ApprovalStatus.pending.value

    decided = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"status": ApprovalStatus.approved.value, "reviewed_by": "admin-1"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == ApprovalStatus.approved.value

    listing = client.get(f"/api/v1/approvals/runs/{run_id}")
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == approval_id


def test_sensitive_tool_step_fails_without_approval(client):
    response = client.post(
        "/api/v1/tasks/submit",
        json={
            "title": "Sensitive operation",
            "description": "perform sensitive export",
            "workflow_name": "default",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    run_id = response.json()["id"]
    sensitive_step = next(step for step in response.json()["steps"] if step["action"] == "sensitive_echo")
    assert sensitive_step["status"] == "failed"

    insights = client.get(f"/api/v1/workflows/runs/{run_id}/insights")
    assert insights.status_code == 200
    assert any("Replan" in action for action in insights.json()["suggested_actions"])
