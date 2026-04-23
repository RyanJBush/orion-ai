import pytest

from app.db import session as db_session_module
from app.models.common import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


def test_task_service_list_returns_latest_first(db_session):
    service = TaskService(db_session)
    older_task = service.create_task(TaskCreate(title="First task", description="d1", priority=TaskPriority.low))
    newer_task = service.create_task(TaskCreate(title="Second task", description="d2", priority=TaskPriority.high))

    tasks = service.list_tasks()

    assert [task.id for task in tasks[:2]] == [newer_task.id, older_task.id]


def test_task_service_set_status_returns_none_for_missing_task(db_session):
    service = TaskService(db_session)
    updated = service.set_status(-1, TaskStatus.running)
    assert updated is None


def test_get_db_closes_session_after_generator_finishes(monkeypatch):
    class DummySession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    dummy = DummySession()
    monkeypatch.setattr(db_session_module, "SessionLocal", lambda: dummy)

    generator = db_session_module.get_db()
    yielded = next(generator)
    assert yielded is dummy

    with pytest.raises(StopIteration):
        next(generator)

    assert dummy.closed is True
