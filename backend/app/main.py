from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, get_db
from app.core.security import create_access_token, require_role
from app.models import Agent, MemoryEntry, RoleEnum, Task, TaskStatus, User, Workflow
from app.schemas import (
    AgentResponse,
    LoginRequest,
    MemoryResponse,
    TaskCreate,
    TaskResponse,
    TokenResponse,
    WorkflowExecuteRequest,
    WorkflowResponse,
)
from app.services.memory import MemoryService
from app.services.tools import ToolRegistry
from app.services.workflow import WorkflowEngine

app = FastAPI(title="Orion AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tools = ToolRegistry()
memory_service = MemoryService()
workflow_engine = WorkflowEngine(tools, memory_service)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Agent).count():
        db.add_all(
            [
                Agent(name="planner-1", role="planner", status="active"),
                Agent(name="worker-1", role="worker", status="active"),
                Agent(name="worker-2", role="worker", status="idle"),
            ]
        )
    if not db.query(User).filter(User.email == "admin@orion.ai").first():
        db.add(User(email="admin@orion.ai", role=RoleEnum.admin))
    db.commit()
    db.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(email=payload.email, role=payload.role)
        db.add(user)
        db.commit()
        db.refresh(user)
    role = user.role.value if isinstance(user.role, RoleEnum) else str(user.role)
    token = create_access_token(str(user.id), role)
    return TokenResponse(access_token=token)


@app.post(
    "/api/tasks",
    response_model=TaskResponse,
    dependencies=[Depends(require_role({"admin", "operator"}))],
)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    task = Task(title=payload.title, description=payload.description, status=TaskStatus.pending)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get(
    "/api/tasks",
    response_model=list[TaskResponse],
    dependencies=[Depends(require_role({"admin", "operator", "viewer"}))],
)
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return db.query(Task).order_by(Task.id.desc()).all()


@app.get(
    "/api/tasks/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_role({"admin", "operator", "viewer"}))],
)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post(
    "/api/workflows/execute",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_role({"admin", "operator"}))],
)
def execute_workflow(payload: WorkflowExecuteRequest, db: Session = Depends(get_db)) -> Workflow:
    task = db.query(Task).filter(Task.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.running
    db.commit()
    db.refresh(task)
    return workflow_engine.execute(db, task)


@app.get(
    "/api/workflows/{workflow_id}",
    response_model=WorkflowResponse,
    dependencies=[Depends(require_role({"admin", "operator", "viewer"}))],
)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)) -> Workflow:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.get(
    "/api/agents",
    response_model=list[AgentResponse],
    dependencies=[Depends(require_role({"admin", "operator", "viewer"}))],
)
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    return db.query(Agent).order_by(Agent.id.asc()).all()


@app.get(
    "/api/memory/{task_id}",
    response_model=MemoryResponse,
    dependencies=[Depends(require_role({"admin", "operator", "viewer"}))],
)
def list_memory(task_id: int, db: Session = Depends(get_db)) -> MemoryResponse:
    entries = (
        db.query(MemoryEntry)
        .filter(MemoryEntry.task_id == task_id)
        .order_by(MemoryEntry.id.asc())
        .all()
    )
    return MemoryResponse(task_id=task_id, entries=[entry.content for entry in entries])
