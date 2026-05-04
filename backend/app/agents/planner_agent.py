from dataclasses import dataclass

from app.agents.contracts import AgentRequest, AgentResponse, ReasoningTrace


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
    fallback_on_errors: list[str] | None = None


class PlannerAgent:
    name = "planner"
    role = "planner"

    def decompose(self, task_title: str, description: str | None) -> list[PlannedStep]:
        source = description or task_title
        chunks = [part.strip() for part in source.replace(";", ".").split(".") if part.strip()]
        if not chunks:
            chunks = [task_title]

        steps: list[PlannedStep] = []
        previous_step_id: str | None = None
        for idx, chunk in enumerate(chunks, start=1):
            chunk_lower = chunk.lower()
            if any(token in chunk_lower for token in ["sensitive", "approve", "approval"]):
                action = "sensitive_echo"
                worker = "worker-general"
            elif "flaky" in chunk_lower:
                action = "flaky"
                worker = "worker-general"
            elif any(token in chunk_lower for token in ["search", "research", "find", "lookup", "discover", "vendor"]):
                action = "web_search"
                worker = "worker-general"
            elif any(token in chunk_lower for token in ["http", "api", "fetch", "call", "request", "endpoint"]):
                action = "http_api"
                worker = "worker-general"
            elif any(token in chunk_lower for token in ["code", "compute", "eval", "calculate", "expression"]):
                action = "code_run"
                worker = "worker-math"
            elif any(ch.isdigit() for ch in chunk):
                action = "math"
                worker = "worker-math"
            else:
                action = "echo"
                worker = "worker-general"

            step_id = f"step-{idx}"
            depends_on_previous = chunk.lower().startswith(("then ", "after ", "next "))
            dependencies = [previous_step_id] if depends_on_previous and previous_step_id else []
            retry_policy = RetryPolicy(max_retries=2 if action in {"math", "flaky", "code_run"} else 1, backoff_seconds=0.05)
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
                    fallback_action="echo" if action in {"flaky", "slow_echo", "web_search", "http_api"} else None,
                    fallback_on_errors=["timeout", "runtime"] if action in {"flaky", "slow_echo", "web_search", "http_api"} else None,
                )
            )
            previous_step_id = step_id
        return steps

    def plan(self, request: AgentRequest) -> AgentResponse:
        steps = self.decompose(task_title=request.goal, description=request.context.get("description"))
        return AgentResponse(
            agent=self.name,
            role=self.role,
            status="completed",
            output={
                "workflow_goal": request.goal,
                "step_count": len(steps),
                "steps": [
                    {
                        "id": step.id,
                        "order": step.order,
                        "owner": step.owner,
                        "action": step.action,
                        "instruction": step.instruction,
                        "dependencies": step.dependencies,
                        "retry": {
                            "max_retries": step.retry_policy.max_retries,
                            "backoff_seconds": step.retry_policy.backoff_seconds,
                        },
                    }
                    for step in steps
                ],
            },
            reasoning_trace=ReasoningTrace(
                summary="Task decomposed into executable steps grouped by tool/action type.",
                confidence=0.81,
                tags=["decomposition", "routing", "retry-policy"],
            ),
        )


planner_agent = PlannerAgent()
