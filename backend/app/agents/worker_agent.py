from dataclasses import dataclass

from app.tools.registry import tool_registry


@dataclass
class WorkerResult:
    output: str
    tool_name: str


class WorkerAgent:
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
