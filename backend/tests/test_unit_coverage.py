"""
Comprehensive unit tests covering areas previously missing from the test suite:
- core/security.py  (JWT creation, validation, role guard)
- core/logging.py   (configure_logging)
- AuditService.redact
- MemoryService internals (_embed, _cosine, _resolve_expiry)
- PlannerAgent edge cases
- WorkflowEngine static helpers (_error_code_for_failure_class, _format_error, _validate_plan)
- WorkflowInsightService quality score scenarios
- UsageService.consume_run success path
- orchestration_service.build_langgraph_stub
- Default tool unit tests (EchoTool, MathTool floats, FlakyTool recovery)
- ToolSchema defaults and Tool.healthcheck default
- ApprovalService.decide edge cases
"""

import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.agents.planner_agent import PlannerAgent, planner_agent
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import create_access_token, get_current_user, require_role
from app.models.common import (
    ApprovalStatus,
    MemoryScope,
    MemoryType,
    StepStatus,
    WorkflowRunStatus,
)
from app.schemas.workflow import ExecutionStep, WorkflowRun
from app.services.approval_service import ToolApprovalService
from app.services.audit_service import AuditService
from app.services.memory_service import MemoryService
from app.services.orchestration_service import build_langgraph_stub
from app.schemas.usage import UsageQuotaSetRequest
from app.services.usage_service import QuotaExceededError, UsageService
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_insight_service import WorkflowInsightService
from app.tools.base import Tool, ToolSchema
from app.tools.default_tools import EchoTool, FlakyTool, MathTool, SensitiveEchoTool, SlowEchoTool


# ---------------------------------------------------------------------------
# core/security.py
# ---------------------------------------------------------------------------


def test_create_access_token_encodes_subject_and_role():
    token = create_access_token("user-42", "admin", expires_minutes=10)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "user-42"
    assert payload["role"] == "admin"


def test_create_access_token_has_future_expiry():
    token = create_access_token("u1", "viewer", expires_minutes=30)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["exp"] > datetime.now(tz=timezone.utc).timestamp()


def test_get_current_user_returns_user_for_valid_token():
    token = create_access_token("user-99", "editor")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    assert user["id"] == "user-99"
    assert user["role"] == "editor"


def test_get_current_user_raises_401_for_none_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


def test_get_current_user_raises_401_for_invalid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


def test_get_current_user_raises_401_for_expired_token():
    expired_payload = {
        "sub": "expired-user",
        "role": "viewer",
        "iat": datetime.now(tz=timezone.utc) - timedelta(minutes=120),
        "exp": datetime.now(tz=timezone.utc) - timedelta(minutes=60),
    }
    token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_require_role_passes_for_matching_role():
    token = create_access_token("admin-user", "admin")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    guard = require_role({"admin", "superuser"})
    result = guard(user)
    assert result["id"] == "admin-user"


def test_require_role_raises_403_for_insufficient_role():
    token = create_access_token("regular-user", "viewer")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    guard = require_role({"admin"})
    with pytest.raises(HTTPException) as exc_info:
        guard(user)
    assert exc_info.value.status_code == 403
    assert "Insufficient permissions" in exc_info.value.detail


# ---------------------------------------------------------------------------
# core/logging.py
# ---------------------------------------------------------------------------


def test_configure_logging_does_not_raise():
    configure_logging()
    root_logger = logging.getLogger()
    assert root_logger.level != logging.NOTSET


# ---------------------------------------------------------------------------
# AuditService.redact
# ---------------------------------------------------------------------------


def test_redact_replaces_ssn():
    redacted = AuditService.redact("SSN: 123-45-6789 is confidential")
    assert "123-45-6789" not in redacted
    assert "***-**-****" in redacted


def test_redact_replaces_16_digit_card_number():
    redacted = AuditService.redact("card=4111111111111111")
    assert "4111111111111111" not in redacted
    assert "****" in redacted


def test_redact_replaces_12_digit_card_number():
    redacted = AuditService.redact("ref=123456789012")
    assert "123456789012" not in redacted
    assert "****" in redacted


def test_redact_leaves_short_numbers_intact():
    text = "order=12345"
    assert AuditService.redact(text) == text


def test_redact_handles_text_with_no_sensitive_data():
    text = "normal audit event for workflow run"
    assert AuditService.redact(text) == text


def test_redact_replaces_both_ssn_and_card_in_same_string():
    text = "ssn=123-45-6789 and card=4111111111111111"
    redacted = AuditService.redact(text)
    assert "123-45-6789" not in redacted
    assert "4111111111111111" not in redacted


# ---------------------------------------------------------------------------
# MemoryService internals
# ---------------------------------------------------------------------------


def test_embed_returns_fixed_length_vector():
    vec = MemoryService._embed("workflow task agent")
    assert len(vec) == 8


def test_embed_counts_known_vocabulary_tokens():
    vec = MemoryService._embed("task task workflow")
    # vocabulary order: task, workflow, agent, memory, tool, run, step, error
    assert vec[0] == 2.0  # "task" appears twice
    assert vec[1] == 1.0  # "workflow" appears once
    assert vec[2] == 0.0  # "agent" not present


def test_embed_ignores_unknown_tokens():
    vec = MemoryService._embed("lorem ipsum dolor sit amet")
    assert all(v == 0.0 for v in vec)


def test_cosine_identical_vectors():
    v = [1.0, 0.0, 1.0]
    assert MemoryService._cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert MemoryService._cosine(a, b) == pytest.approx(0.0)


def test_cosine_zero_vector_returns_zero():
    zero = [0.0, 0.0, 0.0]
    other = [1.0, 0.0, 0.0]
    assert MemoryService._cosine(zero, other) == 0.0
    assert MemoryService._cosine(other, zero) == 0.0


def test_resolve_expiry_long_term_returns_none():
    result = MemoryService._resolve_expiry(MemoryScope.long_term, None)
    assert result is None


def test_resolve_expiry_short_term_returns_future_datetime():
    before = datetime.now(timezone.utc)
    result = MemoryService._resolve_expiry(MemoryScope.short_term, None)
    assert result is not None
    assert result > before


def test_resolve_expiry_short_term_respects_custom_ttl():
    result = MemoryService._resolve_expiry(MemoryScope.short_term, 3600)
    expected_min = datetime.now(timezone.utc) + timedelta(seconds=3590)
    expected_max = datetime.now(timezone.utc) + timedelta(seconds=3610)
    assert expected_min < result < expected_max


def test_resolve_expiry_clamps_ttl_to_minimum_of_one_second():
    result = MemoryService._resolve_expiry(MemoryScope.short_term, 0)
    assert result is not None
    assert result > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# PlannerAgent edge cases
# ---------------------------------------------------------------------------


def test_planner_uses_title_when_description_is_none():
    steps = planner_agent.decompose("echo hello", None)
    assert len(steps) == 1
    assert steps[0].action == "echo"
    assert steps[0].instruction == "echo hello"


def test_planner_uses_title_when_description_is_empty():
    steps = planner_agent.decompose("fallback title", "")
    assert len(steps) == 1
    assert steps[0].instruction == "fallback title"


def test_planner_routes_flaky_keyword_to_flaky_action():
    steps = planner_agent.decompose("test", "flaky downstream call")
    assert steps[0].action == "flaky"
    assert steps[0].owner == "worker-general"


def test_planner_assigns_fallback_action_for_flaky_steps():
    steps = planner_agent.decompose("test", "flaky integration")
    assert steps[0].fallback_action == "echo"
    assert "runtime" in steps[0].fallback_on_errors


def test_planner_does_not_assign_fallback_for_echo_steps():
    steps = planner_agent.decompose("test", "plain echo step")
    assert steps[0].action == "echo"
    assert steps[0].fallback_action is None


def test_planner_detects_then_dependency():
    steps = planner_agent.decompose("test", "get data. then process result")
    assert steps[0].id == "step-1"
    assert steps[1].id == "step-2"
    assert steps[1].dependencies == ["step-1"]


def test_planner_detects_after_dependency():
    steps = planner_agent.decompose("test", "fetch. after fetch summarize")
    assert "step-1" in steps[1].dependencies


def test_planner_step_ids_are_sequential():
    steps = planner_agent.decompose("test", "a. b. c")
    assert [step.id for step in steps] == ["step-1", "step-2", "step-3"]


def test_planner_assigns_correct_retry_for_math():
    steps = planner_agent.decompose("test", "calculate 5 + 10")
    math_step = next(s for s in steps if s.action == "math")
    assert math_step.retry_policy.max_retries == 2


def test_planner_assigns_lower_retry_for_echo():
    steps = planner_agent.decompose("test", "echo a result")
    assert steps[0].retry_policy.max_retries == 1


# ---------------------------------------------------------------------------
# WorkflowEngine static helpers
# ---------------------------------------------------------------------------


def test_error_code_for_timeout():
    assert WorkflowEngine._error_code_for_failure_class("timeout") == "ORION_TOOL_TIMEOUT"


def test_error_code_for_runtime():
    assert WorkflowEngine._error_code_for_failure_class("runtime") == "ORION_TOOL_RUNTIME"


def test_error_code_for_permission():
    assert WorkflowEngine._error_code_for_failure_class("permission") == "ORION_TOOL_PERMISSION"


def test_error_code_for_canceled():
    assert WorkflowEngine._error_code_for_failure_class("canceled") == "ORION_WORKFLOW_CANCELED"


def test_error_code_for_blocked():
    assert WorkflowEngine._error_code_for_failure_class("blocked") == "ORION_WORKFLOW_BLOCKED"


def test_error_code_for_unknown_falls_back_to_generic():
    assert WorkflowEngine._error_code_for_failure_class("something_unknown") == "ORION_WORKFLOW_ERROR"


def test_error_code_for_none_treats_as_runtime():
    # None is coerced to "runtime" via `failure_class or "runtime"` in the implementation
    assert WorkflowEngine._error_code_for_failure_class(None) == "ORION_TOOL_RUNTIME"


def test_format_error_returns_none_for_empty_message():
    assert WorkflowEngine._format_error(failure_class="runtime", message=None) is None
    assert WorkflowEngine._format_error(failure_class="runtime", message="") is None


def test_format_error_prefixes_error_code():
    result = WorkflowEngine._format_error(failure_class="timeout", message="tool timed out")
    assert result == "[ORION_TOOL_TIMEOUT] tool timed out"


def test_validate_plan_raises_for_unknown_dependency(db_session):
    from app.agents.planner_agent import PlannedStep, RetryPolicy

    engine = WorkflowEngine(db_session)
    steps = [
        PlannedStep(
            id="step-1",
            order=1,
            owner="worker-general",
            action="echo",
            instruction="hello",
            dependencies=["step-99"],  # non-existent
            expected_output="x",
            completion_criteria="done",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.01),
        )
    ]
    with pytest.raises(ValueError, match="unknown dependencies"):
        engine._validate_plan(steps)


def test_validate_plan_raises_for_cyclic_dependency(db_session):
    from app.agents.planner_agent import PlannedStep, RetryPolicy

    engine = WorkflowEngine(db_session)
    steps = [
        PlannedStep(
            id="step-1",
            order=1,
            owner="worker-general",
            action="echo",
            instruction="a",
            dependencies=["step-2"],
            expected_output="x",
            completion_criteria="done",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.01),
        ),
        PlannedStep(
            id="step-2",
            order=2,
            owner="worker-general",
            action="echo",
            instruction="b",
            dependencies=["step-1"],
            expected_output="x",
            completion_criteria="done",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.01),
        ),
    ]
    with pytest.raises(ValueError, match="cycle detected"):
        engine._validate_plan(steps)


def test_validate_plan_passes_for_valid_sequential_steps(db_session):
    from app.agents.planner_agent import PlannedStep, RetryPolicy

    engine = WorkflowEngine(db_session)
    steps = [
        PlannedStep(
            id="step-1",
            order=1,
            owner="worker-general",
            action="echo",
            instruction="a",
            dependencies=[],
            expected_output="x",
            completion_criteria="done",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.01),
        ),
        PlannedStep(
            id="step-2",
            order=2,
            owner="worker-general",
            action="echo",
            instruction="b",
            dependencies=["step-1"],
            expected_output="x",
            completion_criteria="done",
            retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0.01),
        ),
    ]
    engine._validate_plan(steps)  # should not raise


# ---------------------------------------------------------------------------
# WorkflowInsightService – quality score scenarios
# ---------------------------------------------------------------------------


def _make_run(*, run_id: int, status: WorkflowRunStatus, steps: list[ExecutionStep]) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        workflow_name="default",
        task_id=1,
        trace_id=f"trace-{run_id}",
        status=status,
        steps=steps,
    )


def _make_step(
    *,
    step_id: str,
    status: StepStatus,
    attempt_count: int = 1,
    fallback_action: str | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        id=1,
        step_id=step_id,
        step_order=1,
        worker_name="worker-general",
        action="echo",
        input_text="x",
        expected_output="y",
        completion_criteria="done",
        output_text="",
        status=status,
        attempt_count=attempt_count,
        fallback_action=fallback_action,
    )


def test_insight_quality_score_strong_for_all_completed(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=1,
        status=WorkflowRunStatus.completed,
        steps=[_make_step(step_id="step-1", status=StepStatus.completed)],
    )
    insight = service.build_insight(run)
    assert insight.quality_score >= 0.8
    assert "strong" in insight.reflection


def test_insight_quality_score_low_for_mostly_failed(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=2,
        status=WorkflowRunStatus.failed,
        steps=[
            _make_step(step_id="step-1", status=StepStatus.failed),
            _make_step(step_id="step-2", status=StepStatus.failed),
            _make_step(step_id="step-3", status=StepStatus.failed),
        ],
    )
    insight = service.build_insight(run)
    assert insight.quality_score < 0.5
    assert "low" in insight.reflection


def test_insight_quality_score_moderate_for_partial_success(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=3,
        status=WorkflowRunStatus.failed,
        steps=[
            _make_step(step_id="step-1", status=StepStatus.completed),
            _make_step(step_id="step-2", status=StepStatus.completed),
            _make_step(step_id="step-3", status=StepStatus.failed),
            _make_step(step_id="step-4", status=StepStatus.completed),
        ],
    )
    insight = service.build_insight(run)
    assert 0.5 <= insight.quality_score < 0.8
    assert "moderate" in insight.reflection


def test_insight_suggests_retry_policy_review_when_retried(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=4,
        status=WorkflowRunStatus.completed,
        steps=[_make_step(step_id="step-1", status=StepStatus.completed, attempt_count=3)],
    )
    insight = service.build_insight(run)
    assert any("Increase timeout/backoff" in action for action in insight.suggested_actions)


def test_insight_no_replan_suggestion_when_completed(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=5,
        status=WorkflowRunStatus.completed,
        steps=[_make_step(step_id="step-1", status=StepStatus.completed)],
    )
    insight = service.build_insight(run)
    assert not any("Replan" in action for action in insight.suggested_actions)


def test_insight_fallback_suggestion_only_when_failed_and_has_fallback(db_session):
    service = WorkflowInsightService(db_session)
    run = _make_run(
        run_id=6,
        status=WorkflowRunStatus.failed,
        steps=[_make_step(step_id="step-1", status=StepStatus.failed, fallback_action="echo")],
    )
    insight = service.build_insight(run)
    assert any("fallback" in action.lower() for action in insight.suggested_actions)


# ---------------------------------------------------------------------------
# UsageService – consume_run success path
# ---------------------------------------------------------------------------


def test_usage_service_consume_run_increments_used_runs(db_session):
    service = UsageService(db_session)
    before = service.get_quota("test-actor-a")
    assert before.used_runs == 0

    after = service.consume_run("test-actor-a")
    assert after.used_runs == 1
    assert after.remaining_runs == after.max_runs - 1


def test_usage_service_consume_run_raises_when_quota_exceeded(db_session):
    service = UsageService(db_session)
    service.set_quota(UsageQuotaSetRequest(actor_id="limited-actor", max_runs=1))
    service.consume_run("limited-actor")
    with pytest.raises(QuotaExceededError):
        service.consume_run("limited-actor")


def test_usage_service_remaining_runs_never_negative(db_session):
    service = UsageService(db_session)
    service.set_quota(UsageQuotaSetRequest(actor_id="zero-actor", max_runs=1))
    service.consume_run("zero-actor")
    quota = service.get_quota("zero-actor")
    assert quota.remaining_runs == 0


# ---------------------------------------------------------------------------
# orchestration_service.build_langgraph_stub
# ---------------------------------------------------------------------------


def test_build_langgraph_stub_returns_placeholder_dict():
    result = build_langgraph_stub()
    assert result["framework"] == "langgraph"
    assert result["status"] == "placeholder"
    assert "notes" in result


# ---------------------------------------------------------------------------
# Default tool unit tests
# ---------------------------------------------------------------------------


def test_echo_tool_returns_input_unchanged():
    assert EchoTool().run("hello world") == "hello world"


def test_echo_tool_returns_empty_string():
    assert EchoTool().run("") == ""


def test_math_tool_sums_integers():
    assert MathTool().run("add 5 and 7") == "sum=12.0"


def test_math_tool_sums_floats():
    assert MathTool().run("3.5 plus 1.5") == "sum=5.0"


def test_math_tool_handles_negative_numbers():
    result = MathTool().run("-3 + 10")
    assert result == "sum=7.0"


def test_math_tool_returns_no_numbers_message_for_empty_input():
    assert MathTool().run("no numbers here") == "No numeric values found."


def test_flaky_tool_fails_on_first_call_and_recovers():
    tool = FlakyTool()
    with pytest.raises(RuntimeError, match="transient_failure"):
        tool.run("payload")
    result = tool.run("payload")
    assert result == "recovered:payload"


def test_flaky_tool_tracks_attempts_per_input_independently():
    tool = FlakyTool()
    with pytest.raises(RuntimeError):
        tool.run("a")
    with pytest.raises(RuntimeError):
        tool.run("b")
    assert tool.run("a") == "recovered:a"
    assert tool.run("b") == "recovered:b"


def test_sensitive_echo_tool_prefixes_approved():
    assert SensitiveEchoTool().run("data") == "approved:data"


# ---------------------------------------------------------------------------
# ToolSchema defaults and Tool.healthcheck default
# ---------------------------------------------------------------------------


def test_tool_schema_default_values():
    schema = ToolSchema(
        name="test",
        description="test tool",
        input_schema={"in": "string"},
        output_schema={"out": "string"},
    )
    assert schema.timeout_seconds == 5.0
    assert schema.allowed_workers == []
    assert schema.is_demo_tool is False
    assert schema.requires_approval is False
    assert schema.risk_level == "low"
    assert schema.estimated_cost_tier == "low"
    assert schema.supports_streaming is False
    assert schema.idempotent is True


def test_tool_default_healthcheck_returns_true():
    class MinimalTool(Tool):
        name = "minimal"

        def run(self, input_text: str) -> str:
            return input_text

    assert MinimalTool().healthcheck() is True


# ---------------------------------------------------------------------------
# ApprovalService.decide edge cases
# ---------------------------------------------------------------------------


def test_approval_service_decide_returns_none_for_pending_status(db_session):
    from app.schemas.approval import ToolApprovalDecision

    service = ToolApprovalService(db_session)
    decision = ToolApprovalDecision(status=ApprovalStatus.pending, reviewed_by="admin")
    result = service.decide(approval_id=1, payload=decision)
    assert result is None


def test_approval_service_decide_returns_none_for_missing_approval(db_session):
    from app.schemas.approval import ToolApprovalDecision

    service = ToolApprovalService(db_session)
    decision = ToolApprovalDecision(status=ApprovalStatus.approved, reviewed_by="admin")
    result = service.decide(approval_id=99999, payload=decision)
    assert result is None


def test_approval_service_has_approval_returns_false_when_no_record(db_session):
    service = ToolApprovalService(db_session)
    assert service.has_approval(run_id=1, step_id="step-1", tool_name="sensitive_echo") is False


def test_approval_service_has_approval_returns_true_after_approval(db_session, client):
    from app.schemas.approval import ToolApprovalRequestCreate

    # Create a run first via the API so we have a valid run_id
    run_resp = client.post(
        "/api/v1/tasks/submit",
        json={"title": "Approval test", "description": "echo one", "workflow_name": "default"},
    )
    assert run_resp.status_code == 200
    run_id = run_resp.json()["id"]

    service = ToolApprovalService(db_session)
    row = service.request(
        ToolApprovalRequestCreate(
            run_id=run_id,
            step_id="step-probe",
            tool_name="sensitive_echo",
            requested_by="tester",
            reason="coverage test",
        )
    )

    from app.schemas.approval import ToolApprovalDecision

    service.decide(row.id, ToolApprovalDecision(status=ApprovalStatus.approved, reviewed_by="admin"))
    assert service.has_approval(run_id=run_id, step_id="step-probe", tool_name="sensitive_echo") is True
