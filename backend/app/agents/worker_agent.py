from dataclasses import dataclass

from app.tools.registry import tool_registry


@dataclass
class WorkerResult:
    output: str
    tool_name: str


class WorkerAgent:
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, action: str, instruction: str) -> WorkerResult:
        tool = tool_registry.get(action)
        output = tool.run(instruction)
        return WorkerResult(output=output, tool_name=action)
