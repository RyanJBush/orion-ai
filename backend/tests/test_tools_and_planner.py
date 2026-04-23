import pytest

from app.agents.planner_agent import planner_agent
from app.agents.worker_agent import WorkerAgent
from app.tools.base import Tool, ToolPermissionError, ToolRuntimeError, ToolSchema, ToolTimeoutError
from app.tools.default_tools import MathTool, SensitiveEchoTool
from app.tools.registry import ToolRegistry


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


def test_math_tool_returns_message_when_no_numbers_present():
    assert MathTool().run("no digits here") == "No numeric values found."


def test_sensitive_echo_tool_formats_output():
    assert SensitiveEchoTool().run("hello") == "approved:hello"


def test_registry_get_raises_for_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.get("missing-tool")


def test_registry_get_schema_raises_for_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="schema not registered"):
        registry.get_schema("missing-tool")


def test_registry_health_marks_tool_unhealthy_when_healthcheck_raises():
    class BrokenTool(Tool):
        name = "broken"

        def run(self, input_text: str) -> str:
            return input_text

        def healthcheck(self) -> bool:
            raise RuntimeError("boom")

    registry = ToolRegistry()
    registry.register(
        BrokenTool(),
        ToolSchema(
            name="broken",
            description="broken test tool",
            input_schema={"input_text": "string"},
            output_schema={"output_text": "string"},
        ),
    )

    rows = registry.health()
    broken = next(row for row in rows if row["tool"] == "broken")
    assert broken["healthy"] is False
    assert broken["status"] == "unhealthy"


def test_registry_run_wraps_unexpected_exceptions():
    class ExplodingTool(Tool):
        name = "exploding"

        def run(self, input_text: str) -> str:
            raise RuntimeError("explode")

    registry = ToolRegistry()
    registry.register(
        ExplodingTool(),
        ToolSchema(
            name="exploding",
            description="exploding test tool",
            input_schema={"input_text": "string"},
            output_schema={"output_text": "string"},
            allowed_workers=["worker-general"],
        ),
    )

    with pytest.raises(ToolRuntimeError, match="tool 'exploding' failed"):
        registry.run("exploding", worker_name="worker-general", input_text="x")
