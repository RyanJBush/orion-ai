from sqlalchemy.orm import Session

from app.models.common import StepStatus, WorkflowRunStatus
from app.schemas.workflow import WorkflowRun, WorkflowRunInsight


class WorkflowInsightService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_insight(self, run: WorkflowRun) -> WorkflowRunInsight:
        total_steps = max(len(run.steps), 1)
        completed = sum(1 for step in run.steps if step.status == StepStatus.completed)
        failed = sum(1 for step in run.steps if step.status == StepStatus.failed)
        retried = sum(1 for step in run.steps if step.attempt_count > 1)
        fallback_steps = sum(1 for step in run.steps if step.fallback_action)

        completion_ratio = completed / total_steps
        quality_score = max(0.0, min(1.0, completion_ratio - (0.15 * failed) - (0.05 * retried)))

        summary = (
            f"Run {run.id} ({run.trace_id}) executed {len(run.steps)} steps with status {run.status.value}. "
            f"Completed={completed}, failed={failed}, retried={retried}."
        )

        plan_explanation = (
            "Plan ordering followed declared dependencies; independent steps were eligible for parallel execution, "
            "with retries and fallback policies applied where configured."
        )

        reflection = (
            "Execution quality is strong and stable."
            if quality_score >= 0.8
            else "Execution quality is moderate; consider tightening prompts and tool routing."
            if quality_score >= 0.5
            else "Execution quality is low; inspect failed steps and consider replanning."
        )

        suggestions: list[str] = []
        if run.status in {WorkflowRunStatus.failed, WorkflowRunStatus.blocked}:
            suggestions.append("Replan from first failed step and regenerate downstream dependencies.")
        if retried > 0:
            suggestions.append("Increase timeout/backoff for unstable tools and review retry policies.")
        if fallback_steps > 0 and failed > 0:
            suggestions.append("Add additional fallback actions for failure classes not currently covered.")
        if not suggestions:
            suggestions.append("No immediate corrective action required; monitor latency and cost trends.")

        return WorkflowRunInsight(
            run_id=run.id,
            trace_id=run.trace_id,
            summary=summary,
            plan_explanation=plan_explanation,
            quality_score=quality_score,
            reflection=reflection,
            suggested_actions=suggestions,
        )
