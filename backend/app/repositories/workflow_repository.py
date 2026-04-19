from sqlalchemy.orm import Session, joinedload

from app.models.common import StepStatus, WorkflowRunStatus
from app.models.workflow import ExecutionStepModel, WorkflowRunModel


class WorkflowRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(self, workflow_name: str, task_id: int) -> WorkflowRunModel:
        run = WorkflowRunModel(workflow_name=workflow_name, task_id=task_id, status=WorkflowRunStatus.queued)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def set_run_status(self, run: WorkflowRunModel, status: WorkflowRunStatus) -> WorkflowRunModel:
        run.status = status
        self.db.commit()
        self.db.refresh(run)
        return run

    def add_step(
        self,
        run_id: int,
        step_order: int,
        worker_name: str,
        action: str,
        input_text: str,
        status: StepStatus = StepStatus.queued,
        output_text: str = "",
    ) -> ExecutionStepModel:
        step = ExecutionStepModel(
            run_id=run_id,
            step_order=step_order,
            worker_name=worker_name,
            action=action,
            input_text=input_text,
            output_text=output_text,
            status=status,
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def update_step(self, step: ExecutionStepModel, status: StepStatus, output_text: str) -> ExecutionStepModel:
        step.status = status
        step.output_text = output_text
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_run(self, run_id: int) -> WorkflowRunModel | None:
        return (
            self.db.query(WorkflowRunModel)
            .options(joinedload(WorkflowRunModel.steps))
            .filter(WorkflowRunModel.id == run_id)
            .first()
        )
