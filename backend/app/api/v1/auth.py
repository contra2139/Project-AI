from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from datetime import timedelta
import os
import logging
from typing import Any

from app.utils.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    store_refresh_token, 
    revoke_refresh_token,
    verify_refresh_token,
    check_login_rate_limit
)
from app.api.dependencies import get_current_user, get_redis
from app.schemas.auth import LoginRequest, LoginResponse, TokenData, UserInfo

router = APIRouter()
logger = logging.getLogger(__name__)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
# Use os.getenv and a fallback that is definitely valid if not set
DEFAULT_HASH = "$pbkdf2-sha256$29000$hBAiZOz9H0Oo9V6rNca4lw$XjBRO8LLdCfNqDiYb2eAYX6PVwopd5o8oevKY6cVtm5o"
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", DEFAULT_HASH)
# Strip any potential whitespace or trailing characters that might cause malformed hash errors
ADMIN_PASSWORD_HASH = ADMIN_PASSWORD_HASH.strip()

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    redis=Depends(get_redis)
):
    # 1. Rate Limiting check (Redis-based)
    client_ip = request.client.host
    if not await check_login_rate_limit(client_ip, redis):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    # 2. Verify Credentials
    if login_data.username != ADMIN_USERNAME or not verify_password(login_data.password, ADMIN_PASSWORD_HASH):
        logger.warning(f"Failed login attempt for username: {login_data.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # 3. Create Tokens
    access_token = create_access_token(data={"sub": ADMIN_USERNAME})
    refresh_token = create_refresh_token(user_id=ADMIN_USERNAME)

    # 4. Store Refresh Token in Redis
    await store_refresh_token(refresh_token, ADMIN_USERNAME, redis)

    # 5. Set httpOnly Cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, # Should be True in production
        samesite="lax",
        max_age=30 * 24 * 3600 # 30 days
    )

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60)) * 60
        }
    }

@router.post("/refresh")
async def refresh(
    request: Request,
    redis=Depends(get_redis)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    user_id = await verify_refresh_token(refresh_token, redis)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Create new access token
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "expires_in": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60)) * 60
        }
    }

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    redis=Depends(get_redis)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_refresh_token(refresh_token, redis)
    
    response.delete_cookie("refresh_token")
    return {"success": True, "message": "Logged out"}

@router.get("/me", response_model=UserInfo)
async def get_me(current_user: str = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "user_id": current_user,
            "username": ADMIN_USERNAME,
            "role": "admin"
        }
    }
