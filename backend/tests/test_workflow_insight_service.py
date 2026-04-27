from app.models.common import StepStatus, WorkflowRunStatus
from app.schemas.workflow import ExecutionStep, WorkflowRun
from app.services.workflow_insight_service import WorkflowInsightService


def test_build_insight_adds_retry_and_fallback_suggestions(db_session):
    service = WorkflowInsightService(db_session)
    run = WorkflowRun(
        id=101,
        workflow_name="default",
        task_id=1,
        trace_id="trace-101",
        status=WorkflowRunStatus.failed,
        steps=[
            ExecutionStep(
                id=1,
                step_id="step-1",
                step_order=1,
                worker_name="worker-general",
                action="echo",
                input_text="x",
                expected_output="y",
                completion_criteria="done",
                output_text="",
                status=StepStatus.failed,
                attempt_count=2,
                fallback_action="use-other-tool",
            )
        ],
    )

    insight = service.build_insight(run)

    assert any("Replan" in action for action in insight.suggested_actions)
    assert any("Increase timeout/backoff" in action for action in insight.suggested_actions)
    assert any("Add additional fallback actions" in action for action in insight.suggested_actions)


def test_build_insight_handles_runs_without_steps(db_session):
    service = WorkflowInsightService(db_session)
    run = WorkflowRun(
        id=202,
        workflow_name="default",
        task_id=2,
        trace_id="trace-202",
        status=WorkflowRunStatus.completed,
        steps=[],
    )

    insight = service.build_insight(run)

    assert insight.quality_score == 0.0
    assert "executed 0 steps" in insight.summary
    assert insight.suggested_actions == ["No immediate corrective action required; monitor latency and cost trends."]
