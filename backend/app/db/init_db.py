from app.db.base import Base
from app.db.session import engine
from app.models import AgentModel, ExecutionStepModel, MemoryEntryModel, TaskModel, VectorMemoryModel, WorkflowModel, WorkflowRunModel


def init_db() -> None:
    _ = (AgentModel, ExecutionStepModel, MemoryEntryModel, TaskModel, VectorMemoryModel, WorkflowModel, WorkflowRunModel)
    Base.metadata.create_all(bind=engine)
