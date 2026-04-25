from app.db.base import Base
from app.db.session import engine
from app.models import (
    AgentModel,
    AuditLogModel,
    ExecutionStepModel,
    MemoryEntryModel,
    TaskModel,
    ToolApprovalModel,
    UsageQuotaModel,
    VectorMemoryModel,
    WorkflowModel,
    WorkflowRunModel,
    WorkflowTemplateModel,
    WorkflowTimelineEventModel,
)


def init_db() -> None:
    # Ensure model metadata is fully loaded before table creation.
    _ = (
        AgentModel,
        AuditLogModel,
        ExecutionStepModel,
        MemoryEntryModel,
        TaskModel,
        ToolApprovalModel,
        UsageQuotaModel,
        VectorMemoryModel,
        WorkflowModel,
        WorkflowRunModel,
        WorkflowTemplateModel,
        WorkflowTimelineEventModel,
    )
    Base.metadata.create_all(bind=engine)
