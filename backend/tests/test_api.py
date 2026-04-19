import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB = Path(__file__).parent / "test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position


def get_token(client: TestClient, role: str = "operator") -> str:
    response = client.post("/api/auth/login", json={"email": f"{role}@orion.ai", "role": role})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_task_and_workflow_flow() -> None:
    with TestClient(app) as client:
        token = get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_task = client.post(
            "/api/tasks",
            headers=headers,
            json={"title": "Investigate drift", "description": "Run diagnostics against pipeline"},
        )
        assert create_task.status_code == 200
        task = create_task.json()

        execute = client.post(
            "/api/workflows/execute",
            headers=headers,
            json={"task_id": task["id"]},
        )
        assert execute.status_code == 200
        workflow = execute.json()
        assert workflow["status"] == "completed"

        memory = client.get(f"/api/memory/{task['id']}", headers=headers)
        assert memory.status_code == 200
        assert len(memory.json()["entries"]) >= 1
