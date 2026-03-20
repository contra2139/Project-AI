import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

# Setup dummy environment
os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = "$2b$12$LQv3c1yqBWVHxkd0LNJ36uEdExYTr1yXvS.S3yv0.yv0.yv0.yv0."

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.api.dependencies import get_redis, get_db

mock_redis = AsyncMock()
app.dependency_overrides[get_redis] = lambda: mock_redis
app.dependency_overrides[get_db] = lambda: AsyncMock()

client = TestClient(app)

def test_minimal_login():
    mock_redis.incr.return_value = 1
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "password"})
    assert response.status_code == 200
    assert response.json()["success"] is True
