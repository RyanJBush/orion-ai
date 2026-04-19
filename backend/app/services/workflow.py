from sqlalchemy.orm import Session

from app.models import Agent, MemoryEntry, Task, TaskStatus, ToolCall, Workflow, WorkflowStatus
from app.services.memory import MemoryService
from app.services.tools import ToolRegistry


class PlannerAgent:
    @staticmethod
    def create_plan(task: Task) -> list[str]:
        return [
            f"Analyze task: {task.title}",
            "Execute worker tools",
            "Persist memory and report completion",
        ]


class WorkerAgentRunner:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    def run(self, step: str, task: Task) -> str:
        payload = f"{step} | {task.description}"
        tool_name = "summarize" if "Persist" in step else "echo"
        return self.tools.run(tool_name, payload)


class WorkflowEngine:
    def __init__(self, tools: ToolRegistry, memory: MemoryService) -> None:
        self.planner = PlannerAgent()
        self.worker = WorkerAgentRunner(tools)
        self.memory = memory

    def execute(self, db: Session, task: Task) -> Workflow:
        plan_steps = self.planner.create_plan(task)
        workflow = Workflow(
            task_id=task.id,
            plan="\n".join(plan_steps),
            status=WorkflowStatus.running,
        )
        db.add(workflow)
        db.flush()

        worker_agents = db.query(Agent).filter(Agent.role == "worker").all()
        if not worker_agents:
            worker_agents = [Agent(name="worker-1", role="worker", status="active")]
            db.add(worker_agents[0])
            db.flush()

        logs: list[str] = []
        for idx, step in enumerate(plan_steps):
            agent = worker_agents[idx % len(worker_agents)]
            output = self.worker.run(step, task)
            logs.append(f"[{agent.name}] {step} -> {output}")
            db.add(
                ToolCall(
                    workflow_id=workflow.id,
                    agent_id=agent.id,
                    tool_name="summarize" if "Persist" in step else "echo",
                    input_payload=task.description,
                    output_payload=output,
                )
            )

        summary = f"Workflow {workflow.id} completed for task {task.id}"
        self.memory.remember(task.id, summary)
        db.add(MemoryEntry(task_id=task.id, content=summary, source="workflow_engine"))

        workflow.execution_log = "\n".join(logs)
        workflow.status = WorkflowStatus.completed
        task.status = TaskStatus.completed
        db.commit()
        db.refresh(workflow)
        return workflow
