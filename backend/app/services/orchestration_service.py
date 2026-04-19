from typing import Any


def build_langgraph_stub() -> dict[str, Any]:
    """Stub that marks where LangGraph/LangChain orchestration is initialized."""
    return {
        "framework": "langgraph",
        "status": "placeholder",
        "notes": "Attach tool nodes, state schema, and checkpointer here.",
    }
