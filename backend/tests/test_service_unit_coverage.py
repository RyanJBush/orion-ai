from datetime import datetime, timezone

import pytest

from app.models.common import ApprovalStatus, MemoryScope, TaskPriority
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRunRepository
from app.schemas.approval import ToolApprovalDecision, ToolApprovalRequestCreate
from app.schemas.common import APIMessage, EntityBase
from app.services.approval_service import ToolApprovalService
from app.services.audit_service import AuditService
from app.services.memory_service import MemoryService
from app.services.orchestration_service import build_langgraph_stub
from app.services.tools import ToolRegistry as LegacyToolRegistry
from app.tools.base import Tool, ToolPermissionError, ToolSchema
from app.tools.default_tools import FlakyTool
from app.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Orchestration service stub
# ---------------------------------------------------------------------------


def test_build_langgraph_stub_returns_expected_keys():
    result = build_langgraph_stub()
    assert result["framework"] == "langgraph"
    assert result["status"] == "placeholder"
    assert "notes" in result


# ---------------------------------------------------------------------------
# schemas/common — APIMessage and EntityBase
# ---------------------------------------------------------------------------


def test_api_message_stores_message_text():
    msg = APIMessage(message="hello world")
    assert msg.message == "hello world"


def test_entity_base_has_auto_populated_id_and_created_at():
    entity = EntityBase()
    assert entity.id is not None
    assert entity.created_at is not None


# ---------------------------------------------------------------------------
# Legacy services/tools ToolRegistry
# ---------------------------------------------------------------------------


def test_legacy_tool_registry_echo_returns_payload():
    registry = LegacyToolRegistry()
    assert registry.run("echo", "hello legacy") == "hello legacy"


def test_legacy_tool_registry_summarize_short_text_returns_prefixed_output():
    registry = LegacyToolRegistry()
    assert registry.run("summarize", "short text") == "summary:short text"


def test_legacy_tool_registry_summarize_long_text_is_truncated():
    registry = LegacyToolRegistry()
    long_text = "x" * 200
    result = registry.run("summarize", long_text)
    assert result.startswith("summary:")
    assert result.endswith("...")
    assert len(result) <= len("summary:") + 140


def test_legacy_tool_registry_unknown_tool_returns_not_found_sentinel():
    registry = LegacyToolRegistry()
    assert registry.run("no_such_tool", "payload") == "tool_not_found:no_such_tool"


# ---------------------------------------------------------------------------
# core/database compatibility re-export
# ---------------------------------------------------------------------------


def test_core_database_module_re_exports_canonical_objects():
    from app.core.database import Base, SessionLocal, engine, get_db  # noqa: F401

    assert Base is not None
    assert engine is not None
    assert SessionLocal is not None
    assert get_db is not None


# ---------------------------------------------------------------------------
# tools/base.py — default healthcheck implementation
# ---------------------------------------------------------------------------


def test_tool_base_healthcheck_returns_true_by_default():
    class MinimalTool(Tool):
        name = "minimal"

        def run(self, input_text: str) -> str:
            return input_text

    assert MinimalTool().healthcheck() is True


# ---------------------------------------------------------------------------
# tools/default_tools.py — FlakyTool second-attempt success path
# ---------------------------------------------------------------------------


def test_flaky_tool_raises_on_first_call_and_recovers_on_second():
    flaky = FlakyTool()
    with pytest.raises(RuntimeError, match="transient_failure"):
        flaky.run("key-a")
    result = flaky.run("key-a")
    assert result == "recovered:key-a"


# ---------------------------------------------------------------------------
# tools/registry.py — healthcheck returns False (not raises)
# ---------------------------------------------------------------------------


def test_tool_registry_marks_unhealthy_when_healthcheck_returns_false():
    class FalseHealthTool(Tool):
        name = "false_health_tool"

        def run(self, input_text: str) -> str:
            return input_text

        def healthcheck(self) -> bool:
            return False

    registry = ToolRegistry()
    registry.register(
        FalseHealthTool(),
        ToolSchema(
            name="false_health_tool",
            description="returns False from healthcheck",
            input_schema={"input_text": "string"},
            output_schema={"output_text": "string"},
        ),
    )
    rows = registry.health()
    row = next(r for r in rows if r["tool"] == "false_health_tool")
    assert row["healthy"] is False
    assert row["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# tools/registry.py — ToolPermissionError raised inside tool.run() is re-raised
# ---------------------------------------------------------------------------


def test_tool_registry_reraises_tool_permission_error_from_tool_run():
    class PermissionDenyingTool(Tool):
        name = "permission_deny_tool"

        def run(self, input_text: str) -> str:
            raise ToolPermissionError("denied from within tool")

    registry = ToolRegistry()
    registry.register(
        PermissionDenyingTool(),
        ToolSchema(
            name="permission_deny_tool",
            description="raises ToolPermissionError internally",
            input_schema={"input_text": "string"},
            output_schema={"output_text": "string"},
            allowed_workers=["worker-general"],
        ),
    )
    with pytest.raises(ToolPermissionError, match="denied from within tool"):
        registry.run("permission_deny_tool", worker_name="worker-general", input_text="x")


# ---------------------------------------------------------------------------
# approval_service.decide — returns None when decision status is pending
# ---------------------------------------------------------------------------


def test_approval_service_decide_returns_none_when_decision_is_pending(db_session):
    task = TaskRepository(db_session).create("t", "d", TaskPriority.normal)
    run = WorkflowRunRepository(db_session).create_run("default", task.id, "trace-approval-pending")
    service = ToolApprovalService(db_session)
    req = service.request(
        ToolApprovalRequestCreate(
            run_id=run.id,
            step_id="step-1",
            tool_name="sensitive_echo",
            requested_by="operator",
            reason="pending decision test",
        )
    )
    result = service.decide(req.id, ToolApprovalDecision(status=ApprovalStatus.pending, reviewed_by="admin"))
    assert result is None


# ---------------------------------------------------------------------------
# memory_service — _cosine static method edge cases
# ---------------------------------------------------------------------------


def test_memory_service_cosine_with_all_zero_vectors_returns_zero():
    assert MemoryService._cosine([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) == 0.0


def test_memory_service_cosine_with_zero_first_vector_returns_zero():
    assert MemoryService._cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_memory_service_cosine_with_zero_second_vector_returns_zero():
    assert MemoryService._cosine([1.0, 0.0], [0.0, 0.0]) == 0.0


def test_memory_service_cosine_with_identical_nonzero_vectors_returns_one():
    score = MemoryService._cosine([1.0, 0.0], [1.0, 0.0])
    assert abs(score - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# memory_service — _resolve_expiry static method
# ---------------------------------------------------------------------------


def test_memory_service_resolve_expiry_long_term_returns_none():
    assert MemoryService._resolve_expiry(MemoryScope.long_term, None) is None


def test_memory_service_resolve_expiry_long_term_ignores_ttl_argument():
    assert MemoryService._resolve_expiry(MemoryScope.long_term, 3600) is None


def test_memory_service_resolve_expiry_short_term_with_explicit_ttl_is_in_the_future():
    result = MemoryService._resolve_expiry(MemoryScope.short_term, 3600)
    assert result is not None
    assert result > datetime.now(timezone.utc)


def test_memory_service_resolve_expiry_short_term_with_zero_ttl_uses_minimum_of_one_second():
    result = MemoryService._resolve_expiry(MemoryScope.short_term, 0)
    assert result is not None
    assert result > datetime.now(timezone.utc)


def test_memory_service_resolve_expiry_short_term_with_none_ttl_uses_default():
    result = MemoryService._resolve_expiry(MemoryScope.short_term, None)
    assert result is not None
    assert result > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# audit_service.redact — SSN and credit-card masking
# ---------------------------------------------------------------------------


def test_audit_service_redact_masks_ssn_pattern():
    redacted = AuditService.redact("SSN is 123-45-6789 in the record")
    assert "123-45-6789" not in redacted
    assert "***-**-****" in redacted


def test_audit_service_redact_preserves_text_without_sensitive_data():
    text = "No sensitive data present here"
    assert AuditService.redact(text) == text


def test_audit_service_redact_masks_credit_card_number():
    redacted = AuditService.redact("card=4111111111111111 processed")
    assert "4111111111111111" not in redacted
    assert "****" in redacted
