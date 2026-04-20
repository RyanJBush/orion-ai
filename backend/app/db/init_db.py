from app.db.base import Base
from app.db.session import engine
from app.models import (
    AgentModel,
    ExecutionStepModel,
    MemoryEntryModel,
    TaskModel,
    VectorMemoryModel,
    WorkflowModel,
    WorkflowRunModel,
    WorkflowTimelineEventModel,
)


def init_db() -> None:
    _ = (
        AgentModel,
        ExecutionStepModel,
        MemoryEntryModel,
        TaskModel,
        VectorMemoryModel,
        WorkflowModel,
        WorkflowRunModel,
        WorkflowTimelineEventModel,
    )
    Base.metadata.create_all(bind=engine)
