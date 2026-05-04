import ast
import json
import re
import time

from app.tools.base import Tool

# ---------------------------------------------------------------------------
# Original demo tools
# ---------------------------------------------------------------------------


class EchoTool(Tool):
    name = "echo"

    def run(self, input_text: str) -> str:
        return input_text


class MathTool(Tool):
    name = "math"

    def run(self, input_text: str) -> str:
        nums = [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", input_text)]
        if not nums:
            return "No numeric values found."
        return f"sum={sum(nums)}"


class SlowEchoTool(Tool):
    name = "slow_echo"

    def run(self, input_text: str) -> str:
        time.sleep(0.2)
        return f"slow:{input_text}"


class FlakyTool(Tool):
    name = "flaky"

    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}

    def run(self, input_text: str) -> str:
        attempt = self._attempts.get(input_text, 0) + 1
        self._attempts[input_text] = attempt
        if attempt == 1:
            raise RuntimeError("transient_failure")
        return f"recovered:{input_text}"


class SensitiveEchoTool(Tool):
    name = "sensitive_echo"

    def run(self, input_text: str) -> str:
        return f"approved:{input_text}"


# ---------------------------------------------------------------------------
# Extended tools — credible demo implementations
# ---------------------------------------------------------------------------

# Canned search results used by WebSearchTool in demo/offline mode.
_SEARCH_CORPUS: dict[str, list[dict[str, str]]] = {
    "default": [
        {"title": "Introduction to AI Agents", "snippet": "AI agents perceive their environment and take actions.", "url": "https://example.com/ai-agents"},
        {"title": "Multi-Agent Systems Overview", "snippet": "Multiple agents collaborate to solve complex tasks.", "url": "https://example.com/mas"},
        {"title": "Workflow Orchestration Patterns", "snippet": "Sequential, parallel, and event-driven workflow patterns.", "url": "https://example.com/workflows"},
    ],
    "observability": [
        {"title": "Datadog vs Grafana", "snippet": "Datadog: $15/host/mo. Grafana Cloud: free tier available.", "url": "https://example.com/observability"},
        {"title": "OpenTelemetry", "snippet": "Open standard for distributed tracing and metrics.", "url": "https://example.com/otel"},
        {"title": "Prometheus Monitoring", "snippet": "Pull-based metrics collection with PromQL query language.", "url": "https://example.com/prometheus"},
    ],
    "incident": [
        {"title": "Incident Trend Analysis", "snippet": "MoM incident counts fell 18% after runbook automation.", "url": "https://example.com/incidents"},
        {"title": "Root Cause Patterns", "snippet": "Top causes: config drift (42%), capacity (31%), deploys (27%).", "url": "https://example.com/rca"},
    ],
}


class WebSearchTool(Tool):
    """Returns structured search results for a query (demo-safe canned responses)."""

    name = "web_search"

    def run(self, input_text: str) -> str:
        query_lower = input_text.lower()
        corpus_key = "default"
        for key in _SEARCH_CORPUS:
            if key in query_lower:
                corpus_key = key
                break
        results = _SEARCH_CORPUS[corpus_key]
        return json.dumps({"query": input_text, "results": results, "source": "demo-corpus"}, indent=2)


class HttpApiTool(Tool):
    """Performs a lightweight HTTP GET against a stub endpoint (demo-safe)."""

    name = "http_api"

    # Stub responses keyed by URL fragment to keep the demo self-contained.
    _STUBS: dict[str, dict] = {
        "metrics": {"status": "ok", "data": {"requests_per_second": 142, "error_rate": 0.002, "p99_latency_ms": 87}},
        "status":  {"status": "ok", "services": {"api": "healthy", "db": "healthy", "cache": "healthy"}},
        "pricing": {"plans": [{"name": "starter", "price": 0}, {"name": "pro", "price": 49}, {"name": "enterprise", "price": 299}]},
    }

    def run(self, input_text: str) -> str:
        url_lower = input_text.lower()
        payload = {"url": input_text, "status_code": 200, "response": {"message": "ok"}}
        for fragment, stub in self._STUBS.items():
            if fragment in url_lower:
                payload["response"] = stub
                break
        return json.dumps(payload, indent=2)


class CodeRunTool(Tool):
    """Safely evaluates simple numeric/arithmetic Python expressions."""

    name = "code_run"

    # Only allow a restricted set of AST node types to prevent code injection.
    _ALLOWED_NODES = frozenset({
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Add, ast.Sub, ast.Mul, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    })

    def _safe_eval(self, expr: str) -> float | int:
        tree = ast.parse(expr.strip(), mode="eval")
        for node in ast.walk(tree):
            if type(node) not in self._ALLOWED_NODES:
                raise ValueError(f"Unsafe expression node: {type(node).__name__}")
        return eval(compile(tree, "<string>", "eval"))  # noqa: S307

    def run(self, input_text: str) -> str:
        # Extract the first code block or fall back to the raw input.
        code_match = re.search(r"```(?:python)?\s*(.*?)```", input_text, re.DOTALL)
        expr = code_match.group(1).strip() if code_match else input_text.strip()
        # Extract a numeric expression from prose if needed.
        expr_match = re.search(r"[0-9][\d\s\+\-\*/\(\)\.\^%]+", expr)
        if expr_match:
            expr = expr_match.group(0).replace("^", "**")
        try:
            result = self._safe_eval(expr)
            return json.dumps({"expression": expr, "result": result, "status": "ok"})
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"expression": expr, "error": str(exc), "status": "error"})
