import os
from datetime import datetime, timedelta
from typing import Optional, Any, Union
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import logging

# Security settings should ideally come from a centralized Settings object
# but for utility purposes, we can read from environment directly or pass them
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is NOT set")
if len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters for security")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT Access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Create a JWT Refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"JWT Decode Error: {str(e)}")
        raise

def _get_token_hash(token: str) -> str:
    """Generate a hash for a token to use as Redis key."""
    return hashlib.sha256(token.encode()).hexdigest()

async def store_refresh_token(token: str, user_id: str, redis_client) -> None:
    """Store refresh token hash in Redis with expiration."""
    token_hash = _get_token_hash(token)
    key = f"refresh:{token_hash}"
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis_client.set(key, user_id, ex=ttl)

async def revoke_refresh_token(token: str, redis_client) -> None:
    """Remove refresh token from Redis."""
    token_hash = _get_token_hash(token)
    key = f"refresh:{token_hash}"
    await redis_client.delete(key)

async def verify_refresh_token(token: str, redis_client) -> Optional[str]:
    """Verify refresh token existence in Redis and return user_id."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return None
        
        token_hash = _get_token_hash(token)
        key = f"refresh:{token_hash}"
        user_id = await redis_client.get(key)
        
        if user_id:
            return user_id.decode() if isinstance(user_id, bytes) else user_id
        return None
    except Exception:
        return None

async def check_login_rate_limit(client_ip: str, redis_client) -> bool:
    """
    Check if login attempts exceed limit (5 per minute) using Redis.
    Returns True if allowed, False if blocked.
    """
    key = f"rate_limit:login:{client_ip}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
    
    return count <= 5
