from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ToolError(Exception):
    pass


class ToolPermissionError(ToolError):
    pass


class ToolTimeoutError(ToolError):
    pass


class ToolRuntimeError(ToolError):
    pass


@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    timeout_seconds: float = 5.0
    allowed_workers: list[str] = field(default_factory=list)
    is_demo_tool: bool = False
    requires_approval: bool = False
    risk_level: str = "low"
    estimated_cost_tier: str = "low"
    supports_streaming: bool = False
    idempotent: bool = True


class Tool(ABC):
    name: str

    @abstractmethod
    def run(self, input_text: str) -> str:
        raise NotImplementedError

    def healthcheck(self) -> bool:
        return True
