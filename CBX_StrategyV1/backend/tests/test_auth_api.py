import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import json

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.security import hash_password

# Setup dummy environment for imports
os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = hash_password("password")

from app.main import app
from app.api.dependencies import get_db, get_redis

# Mock Redis
mock_redis = AsyncMock()

# Mock DB
mock_db = AsyncMock()

# Override dependencies
app.dependency_overrides[get_db] = lambda: mock_db
app.dependency_overrides[get_redis] = lambda: mock_redis

client = TestClient(app)

def test_1_login_success():
    """Test login success với đúng credentials."""
    mock_redis.incr.return_value = 1
    mock_redis.set.return_value = True
    
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in response.cookies
    print("\nTest 1 (Login Success): ✅ PASS")

def test_2_login_fail_invalid_credentials():
    """Test login fail khi sai password."""
    mock_redis.incr.return_value = 1
    
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]
    print("Test 2 (Login Fail): ✅ PASS")

def test_3_login_rate_limit():
    """Test login rate limit (lần thứ 6 từ cùng IP)."""
    # Reset mock
    mock_redis.incr.reset_mock()
    # Giả lập lần thứ 6 trả về 6
    mock_redis.incr.return_value = 6
    
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password"}
    )
    
    assert response.status_code == 429
    assert "Too many login attempts" in response.json()["detail"]
    print("Test 3 (Rate Limit): ✅ PASS")

def test_4_refresh_token_success():
    """Test refresh token lấy access token mới."""
    # Giả lập refresh token hợp lệ trong Redis
    from app.utils.security import create_refresh_token
    rf_token = create_refresh_token("admin")
    mock_redis.get.return_value = b"admin"
    
    client.cookies.set("refresh_token", rf_token)
    response = client.post("/api/v1/auth/refresh")
    
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
    print("Test 4 (Refresh Token): ✅ PASS")

def test_5_protected_route_no_token():
    """Test route bị chặn nếu không có token."""
    response = client.get("/api/v1/symbols/")
    assert response.status_code == 401
    print("Test 5 (Protected Route No Token): ✅ PASS")

def test_6_protected_route_with_token():
    """Test route cho phép nếu có token hợp lệ."""
    from app.utils.security import create_access_token
    token = create_access_token({"sub": "admin"})
    
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: []))
    
    response = client.get(
        "/api/v1/symbols/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    print("Test 6 (Protected Route With Token): ✅ PASS")
