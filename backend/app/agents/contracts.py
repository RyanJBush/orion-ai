from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ReasoningTrace:
    """Concise reasoning summary safe for logs and UI."""

    summary: str
    confidence: float = 0.7
    tags: list[str] = field(default_factory=list)


@dataclass
class AgentRequest:
    workflow_id: str | None
    step_id: str | None
    goal: str
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    agent: str
    role: str
    status: str
    output: dict[str, Any]
    reasoning_trace: ReasoningTrace
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasoning_trace"]["confidence"] = round(payload["reasoning_trace"]["confidence"], 2)
        return payload
