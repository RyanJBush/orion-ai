import pytest

from app.agents.planner_agent import planner_agent
from app.agents.worker_agent import WorkerAgent
from app.tools.base import ToolPermissionError, ToolTimeoutError


def test_planner_decomposes_into_steps():
    steps = planner_agent.decompose("Build dashboard", "draft ui. compute 10 + 12")
    assert len(steps) == 2
    assert steps[1].action == "math"
    assert steps[0].id == "step-1"
    assert steps[0].expected_output
    assert steps[1].retry_policy.max_retries >= 1


def test_planner_routes_sensitive_actions_to_approval_tool():
    steps = planner_agent.decompose("Handle sensitive task", "perform sensitive export")
    assert steps[0].action == "sensitive_echo"


def test_worker_executes_tool():
    worker = WorkerAgent(name="worker-general")
    result = worker.execute(action="echo", instruction="hello")
    assert result.output == "hello"


def test_tool_permissions_block_unauthorized_worker():
    worker = WorkerAgent(name="worker-general")
    with pytest.raises(ToolPermissionError):
        worker.execute(action="math", instruction="1 + 2")


def test_tool_timeout_classification():
    worker = WorkerAgent(name="worker-general")
    with pytest.raises(ToolTimeoutError):
        worker.execute(action="slow_echo", instruction="hello")


def test_tool_registry_endpoint_exposes_permissions_and_timeout(client):
    response = client.get("/api/v1/tools/registry")
    assert response.status_code == 200
    tools = response.json()
    math = next(tool for tool in tools if tool["name"] == "math")
    assert math["allowed_workers"] == ["worker-math"]
    assert math["timeout_seconds"] > 0
    sensitive = next(tool for tool in tools if tool["name"] == "sensitive_echo")
    assert sensitive["requires_approval"] is True
    assert sensitive["risk_level"] == "high"
