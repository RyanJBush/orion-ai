from collections.abc import Callable


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[[str], str]] = {
            "echo": self._echo,
            "summarize": self._summarize,
        }

    def run(self, tool_name: str, payload: str) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"tool_not_found:{tool_name}"
        return tool(payload)

    @staticmethod
    def _echo(payload: str) -> str:
        return payload

    @staticmethod
    def _summarize(payload: str) -> str:
        short = payload if len(payload) <= 140 else f"{payload[:137]}..."
        return f"summary:{short}"
