from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_retries: int
    backoff_seconds: float


@dataclass
class PlannedStep:
    id: str
    order: int
    owner: str
    action: str
    instruction: str
    dependencies: list[str]
    expected_output: str
    completion_criteria: str
    retry_policy: RetryPolicy
    fallback_action: str | None = None


class PlannerAgent:
    name = "planner"

    def decompose(self, task_title: str, description: str | None) -> list[PlannedStep]:
        source = description or task_title
        chunks = [part.strip() for part in source.replace(";", ".").split(".") if part.strip()]
        if not chunks:
            chunks = [task_title]

        steps: list[PlannedStep] = []
        previous_step_id: str | None = None
        for idx, chunk in enumerate(chunks, start=1):
            if "flaky" in chunk.lower():
                action = "flaky"
                worker = "worker-general"
            elif any(ch.isdigit() for ch in chunk):
                action = "math"
                worker = "worker-math"
            else:
                action = "echo"
                worker = "worker-general"

            step_id = f"step-{idx}"
            depends_on_previous = chunk.lower().startswith(("then ", "after ", "next "))
            dependencies = [previous_step_id] if depends_on_previous and previous_step_id else []
            retry_policy = RetryPolicy(max_retries=2 if action in {"math", "flaky"} else 1, backoff_seconds=0.05)
            steps.append(
                PlannedStep(
                    id=step_id,
                    order=idx,
                    owner=worker,
                    action=action,
                    instruction=chunk,
                    dependencies=dependencies,
                    expected_output="A non-empty tool output string.",
                    completion_criteria="Tool call succeeds and returns output.",
                    retry_policy=retry_policy,
                    fallback_action="echo" if action in {"flaky", "slow_echo"} else None,
                )
            )
            previous_step_id = step_id
        return steps


planner_agent = PlannerAgent()
