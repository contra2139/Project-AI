from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging
import redis.asyncio as redis
from typing import Optional, Any

from app.utils.security import decode_token
from app.database import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Shared Redis client
_redis_client: Optional[Any] = None

class RedisMock:
    def __init__(self):
        self._data = {}
        logger.info("Using RedisMock (In-Memory)")

    async def get(self, key: str):
        return self._data.get(key)

    async def set(self, key: str, value: Any, ex: int = None):
        self._data[key] = value
        return True

    async def delete(self, key: str):
        self._data.pop(key, None)
        return 1

    async def incr(self, key: str):
        val = int(self._data.get(key, 0)) + 1
        self._data[key] = val
        return val

    async def expire(self, key: str, seconds: int):
        return True

    async def ping(self):
        return True

async def get_redis():
    """Dependency to get Redis client (with Mock fallback only in dev)."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        is_production = os.getenv("ENV") == "production"
        
        try:
            _redis_client = redis.from_url(redis_url, socket_timeout=2)
            await _redis_client.ping()
        except Exception as e:
            if is_production:
                logger.critical(f"Redis connection failed in PRODUCTION: {e}")
                # Fail hard in production
                raise RuntimeError(f"Critical Service Unavailable: Redis is mandatory in production. Error: {e}")
            
            logger.warning(f"Redis connection failed ({e}) in non-production. Falling back to RedisMock.")
            _redis_client = RedisMock()
    return _redis_client

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate access token and return user_id (sub)."""
    token = auth.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(user_id)
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
