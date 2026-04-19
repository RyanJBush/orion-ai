from app.agents.planner_agent import planner_agent
from app.agents.worker_agent import WorkerAgent


def test_planner_decomposes_into_steps():
    steps = planner_agent.decompose("Build dashboard", "draft ui. compute 10 + 12")
    assert len(steps) == 2
    assert steps[1].action == "math"


def test_worker_executes_tool():
    worker = WorkerAgent(name="worker-general")
    result = worker.execute(action="echo", instruction="hello")
    assert result.output == "hello"
