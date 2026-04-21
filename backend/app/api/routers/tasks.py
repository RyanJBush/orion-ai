from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task import QueueDispatchRequest, Task, TaskCreate, TaskSubmitRequest
from app.schemas.workflow import WorkflowRun
from app.services.task_service import TaskService
from app.services.usage_service import QuotaExceededError, UsageService
from app.services.workflow_engine import WorkflowEngine

router = APIRouter()


@router.get("", response_model=list[Task])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return TaskService(db).list_tasks()


@router.post("", response_model=Task)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    return TaskService(db).create_task(payload)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    task = TaskService(db).get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/submit", response_model=WorkflowRun)
def submit_task(payload: TaskSubmitRequest, db: Session = Depends(get_db)) -> WorkflowRun:
    try:
        UsageService(db).consume_run(payload.actor_id)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    task = TaskService(db).create_task(payload)
    return WorkflowEngine(db).execute_task(task.id, workflow_name=payload.workflow_name)


@router.post("/enqueue", response_model=Task)
def enqueue_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    return TaskService(db).create_task(payload)


@router.post("/dispatch-next", response_model=WorkflowRun)
def dispatch_next_queued_task(payload: QueueDispatchRequest, db: Session = Depends(get_db)) -> WorkflowRun:
    try:
        UsageService(db).consume_run(payload.actor_id)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    task = TaskService(db).pop_next_queued_task()
    if task is None:
        raise HTTPException(status_code=404, detail="No queued tasks available")
    return WorkflowEngine(db).execute_task(task.id, workflow_name=payload.workflow_name)
