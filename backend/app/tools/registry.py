from app.tools.base import Tool
from app.tools.default_tools import EchoTool, MathTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self.register(EchoTool())
        self.register(MathTool())

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]


tool_registry = ToolRegistry()
