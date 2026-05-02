from dataclasses import dataclass

from app.agents.contracts import AgentRequest, AgentResponse, ReasoningTrace
from app.tools.registry import tool_registry


@dataclass
class WorkerResult:
    output: str
    tool_name: str


class WorkerAgent:
    role = "executor"

    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, action: str, instruction: str, timeout_seconds: float | None = None) -> WorkerResult:
        output = tool_registry.run(
            name=action,
            worker_name=self.name,
            input_text=instruction,
            timeout_override=timeout_seconds,
        )
        return WorkerResult(output=output, tool_name=action)

    def run(self, request: AgentRequest) -> AgentResponse:
        action = str(request.context.get("action", "echo"))
        timeout_seconds = request.context.get("timeout_seconds")
        result = self.execute(action=action, instruction=request.goal, timeout_seconds=timeout_seconds)
        return AgentResponse(
            agent=self.name,
            role=self.role,
            status="completed",
            output={
                "tool_name": result.tool_name,
                "result": result.output,
                "step_id": request.step_id,
            },
            reasoning_trace=ReasoningTrace(
                summary="Executor selected and invoked a registered tool for the requested step.",
                confidence=0.79,
                tags=["tool-call", "execution"],
            ),
        )
