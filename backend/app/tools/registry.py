from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging

from app.tools.base import Tool, ToolPermissionError, ToolRuntimeError, ToolSchema, ToolTimeoutError
from app.tools.default_tools import EchoTool, FlakyTool, MathTool, SlowEchoTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._schemas: dict[str, ToolSchema] = {}
        self.register(
            EchoTool(),
            ToolSchema(
                name="echo",
                description="Echo input back as output.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=2.0,
                allowed_workers=["worker-general", "worker-math"],
            ),
        )
        self.register(
            MathTool(),
            ToolSchema(
                name="math",
                description="Extract numbers from text and sum them.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=2.0,
                allowed_workers=["worker-math"],
            ),
        )
        self.register(
            SlowEchoTool(),
            ToolSchema(
                name="slow_echo",
                description="Mock tool that sleeps for timeout testing.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=0.05,
                allowed_workers=["worker-general"],
            ),
        )
        self.register(
            FlakyTool(),
            ToolSchema(
                name="flaky",
                description="Mock tool that fails once, then succeeds.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=1.0,
                allowed_workers=["worker-general"],
            ),
        )

    def register(self, tool: Tool, schema: ToolSchema) -> None:
        self._tools[tool.name] = tool
        self._schemas[tool.name] = schema

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]

    def get_schema(self, name: str) -> ToolSchema:
        if name not in self._schemas:
            raise KeyError(f"Tool '{name}' schema not registered")
        return self._schemas[name]

    def run(self, name: str, worker_name: str, input_text: str, timeout_override: float | None = None) -> str:
        tool = self.get(name)
        schema = self.get_schema(name)
        if schema.allowed_workers and worker_name not in schema.allowed_workers:
            raise ToolPermissionError(f"worker '{worker_name}' is not allowed to run tool '{name}'")

        timeout_seconds = timeout_override if timeout_override is not None else schema.timeout_seconds
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(tool.run, input_text)
                return future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            raise ToolTimeoutError(f"tool '{name}' timed out after {timeout_seconds:.2f}s") from exc
        except ToolPermissionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ToolRuntimeError(f"tool '{name}' failed: {exc}") from exc

    def health(self) -> list[dict[str, str | bool]]:
        rows: list[dict[str, str | bool]] = []
        for name, tool in self._tools.items():
            status = "healthy"
            is_healthy = True
            try:
                is_healthy = tool.healthcheck()
                if not is_healthy:
                    status = "unhealthy"
            except Exception:  # noqa: BLE001
                status = "unhealthy"
                is_healthy = False
                logger.exception("tool.healthcheck_failed", extra={"tool": name})
            rows.append({"tool": name, "healthy": is_healthy, "status": status})
        return rows


tool_registry = ToolRegistry()
