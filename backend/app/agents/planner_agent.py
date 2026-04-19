from dataclasses import dataclass


@dataclass
class PlannedStep:
    order: int
    worker_name: str
    action: str
    instruction: str


class PlannerAgent:
    name = "planner"

    def decompose(self, task_title: str, description: str | None) -> list[PlannedStep]:
        source = description or task_title
        chunks = [part.strip() for part in source.replace(";", ".").split(".") if part.strip()]
        if not chunks:
            chunks = [task_title]

        steps: list[PlannedStep] = []
        for idx, chunk in enumerate(chunks, start=1):
            action = "math" if any(ch.isdigit() for ch in chunk) else "echo"
            worker = "worker-math" if action == "math" else "worker-general"
            steps.append(PlannedStep(order=idx, worker_name=worker, action=action, instruction=chunk))
        return steps


planner_agent = PlannerAgent()
