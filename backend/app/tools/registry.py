from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging

from app.tools.base import Tool, ToolPermissionError, ToolRuntimeError, ToolSchema, ToolTimeoutError
from app.tools.default_tools import (
    CodeExecTool,
    EchoTool,
    FlakyTool,
    HttpRequestTool,
    MathTool,
    SearchTool,
    SensitiveEchoTool,
    SlowEchoTool,
)

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
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
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
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
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
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
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
                is_demo_tool=True,
                estimated_cost_tier="medium",
                supports_streaming=False,
                idempotent=False,
            ),
        )
        self.register(
            SensitiveEchoTool(),
            ToolSchema(
                name="sensitive_echo",
                description="Mock sensitive action requiring explicit approval.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=1.0,
                allowed_workers=["worker-general"],
                is_demo_tool=True,
                requires_approval=True,
                risk_level="high",
                estimated_cost_tier="medium",
                supports_streaming=False,
                idempotent=True,
            ),
        )
        self.register(
            SearchTool(),
            ToolSchema(
                name="search",
                description="Keyword search against a built-in knowledge corpus (demo-safe).",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=2.0,
                allowed_workers=["worker-general", "worker-math"],
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
            ),
        )
        self.register(
            HttpRequestTool(),
            ToolSchema(
                name="http_request",
                description="Simulated HTTP GET against whitelisted mock API endpoints.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=3.0,
                allowed_workers=["worker-general"],
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
            ),
        )
        self.register(
            CodeExecTool(),
            ToolSchema(
                name="code_exec",
                description="Evaluates safe arithmetic expressions in a sandboxed context.",
                input_schema={"input_text": "string"},
                output_schema={"output_text": "string"},
                timeout_seconds=2.0,
                allowed_workers=["worker-math", "worker-general"],
                is_demo_tool=True,
                estimated_cost_tier="low",
                supports_streaming=False,
                idempotent=True,
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

    def list_schemas(self) -> list[ToolSchema]:
        return [self._schemas[name] for name in sorted(self._schemas.keys())]

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
