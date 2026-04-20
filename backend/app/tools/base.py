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


class Tool(ABC):
    name: str

    @abstractmethod
    def run(self, input_text: str) -> str:
        raise NotImplementedError

    def healthcheck(self) -> bool:
        return True
