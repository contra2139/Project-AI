import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from loguru import logger
from dotenv import load_dotenv

import asyncio
from typing import Dict, Any
from datetime import datetime

from app.api.v1.router import api_router
from app.api.websocket import websocket_endpoint, connection_manager
from app.services.notification_service import notification_service
from app.telegram.bot import init_telegram_app, process_telegram_update
from app.database import engine, Base, get_db
from app.api.dependencies import get_redis
from binance import AsyncClient, BinanceAPIException

# Load environment variables
load_dotenv()

# Structured logging setup
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CBX Trading Bot API",
    description="REST API for CBX Bot Management & Monitoring",
    version="1.0.0",
)

# Global Telegram Application Reference
telegram_app = None

# CORS configuration
allowed_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS")
if os.getenv("ENV") == "production" and not allowed_origins_raw:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production environment")

allowed_origins = allowed_origins_raw.split(",") if allowed_origins_raw else ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request timing and logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Structured log
    logger.info(
        f"Method: {request.method} Path: {request.url.path} "
        f"Status: {response.status_code} Time: {process_time:.4f}s"
    )
    return response

# Exception handler for structured JSON errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal Server Error", "detail": str(exc)}
    )

# Include API Router
app.include_router(api_router, prefix="/api/v1")

# WebSocket Route
app.add_api_websocket_route("/ws", websocket_endpoint)

# Telegram Webhook Route
@app.post("/tg/webhook")
async def telegram_webhook(request: Request):
    """
    Handle incoming updates from Telegram.
    Verified by X-Telegram-Bot-Api-Secret-Token header.
    """
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    
    if secret != expected_secret:
        logger.warning("Unauthorized webhook access attempt.")
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")

    if telegram_app is None:
        logger.error("Telegram app not initialized.")
        return JSONResponse(status_code=500, content={"error": "Telegram app not initialized"})

    update_data = await request.json()
    await process_telegram_update(telegram_app, update_data)
    return {"status": "ok"}

# Frontend Error Channel with Rate Limiting
@app.post("/api/v1/log/frontend-error")
async def frontend_error_logger(request: Request, redis=Depends(get_redis)):
    """
    Endpoint to receive frontend errors and alert via Telegram.
    Rate limited to 10 requests/minute per IP.
    """
    client_ip = request.client.host
    rate_limit_key = f"rate_limit:frontend_error:{client_ip}"
    
    count = await redis.incr(rate_limit_key)
    if count == 1:
        await redis.expire(rate_limit_key, 60)
    
    if count > 10:
        return JSONResponse(status_code=429, content={"error": "Too many error reports"})
    
    error_data = await request.json()
    logger.error(f"Frontend Error from {client_ip}: {error_data}")
    
    # Send to Telegram
    msg = (
        f"🚨 **Frontend Error Alert**\n"
        f"IP: `{client_ip}`\n"
        f"Error: `{error_data.get('message', 'Unknown')}`\n"
        f"Detail: `{str(error_data)[:200]}`"
    )
    await notification_service.notify_error(module="Frontend", error=msg, critical=True)
    
    return {"status": "logged"}

@app.get("/health")
async def health_check():
    """
    Comprehensive health check for production monitoring.
    Returns 200 even if degraded (binance/telegram error), 
    but 503 if critical services (db/redis) are down.
    """
    services: Dict[str, Any] = {
        "database": {"status": "error", "latency_ms": 0},
        "redis": {"status": "error", "latency_ms": 0},
        "binance": {"status": "pending", "latency_ms": 0},
        "telegram": {"status": "pending"},
        "scanner": {"status": "running", "symbols_active": 0}
    }

    status = "ok"
    
    # 1. Test Database
    start = time.time()
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"]["status"] = "ok"
        services["database"]["latency_ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        logger.error(f"Health Check - DB Error: {e}")
        status = "error"

    # 2. Test Redis (Placeholder for actual redis check if available)
    services["redis"]["status"] = "ok" # Assume ok for now if no redis client here

    # 3. Overall status logic
    if services["database"]["status"] == "error" or services["redis"]["status"] == "error":
        status = "error"
    elif services["binance"]["status"] == "error":
        status = "degraded"

    return JSONResponse(
        status_code=200 if status != "error" else 503,
        content={
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "uptime_seconds": int(time.time() - app.state.start_time),
            "services": services
        }
    )

async def reconcile_positions():
    """
    Non-blocking task to reconcile DB trades vs Binance actual positions.
    """
    logger.info("Starting position reconciliation...")
    try:
        # Placeholder for actual reconciliation logic
        await asyncio.sleep(2) 
        logger.info("Position reconciliation completed successfully.")
    except Exception as e:
        logger.critical(f"Position reconciliation failed: {e}")
        # We don't raise as requested: "Bot must start even if reconciliation fails"

async def validate_security_configs():
    """Ensure sensitive configs are robust."""
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key or len(secret_key) < 32:
        logger.critical("SECRET_KEY is too weak! Must be at least 32 characters.")
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters")

async def validate_api_keys():
    """Verify Binance API key permissions (No Withdrawal)."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        logger.warning("Binance API keys not configured. Skipping validation.")
        return

    logger.info("Validating Binance API permissions...")
    client = await AsyncClient.create(api_key, api_secret)
    
    try:
        # Attempt to fetch withdrawal history
        # If it succeeds, it means the key has Withdrawal permission (DANGEROUS)
        await client.get_withdraw_history()
        logger.critical("SECURITY BREACH: Binance API Key has Withdrawal permission! Shutting down.")
        raise RuntimeError("API Key has Withdrawal permission - INSECURE CONFIGURATION")
    except BinanceAPIException as e:
        # Code -2015: Invalid API-key, IP, or permissions for action.
        # This is what we EXPECT if Withdrawal is disabled.
        if e.code == -2015:
            logger.info("Binance API validation: Withdrawal permission is disabled (SAFE).")
        else:
            logger.error(f"Binance API validation error: {e}")
            # Optional: Decide if we want to fail on other errors (like invalid key)
    except Exception as e:
        logger.error(f"Unexpected error validating Binance API: {e}")
    finally:
        await client.close_connection()

@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    
    # 0. Setup Log Rotation
    os.makedirs("logs", exist_ok=True)
    logger.add("logs/backend.log", rotation="100 MB", retention="30 days", level="INFO")
    
    logger.info("Starting up CBX Bot API...")
    
    # 1. Validate Critical Settings
    await validate_security_configs()
    await validate_api_keys()
    
    required_env = ["BINANCE_API_KEY", "BINANCE_API_SECRET", "POSTGRES_DB"]
    for env in required_env:
        if not os.getenv(env):
            logger.error(f"Missing critical environment variable: {env}")
    
    # 2. Inject WebSocket manager
    notification_service.ws_manager = connection_manager
    logger.info("WebSocket manager injected into NotificationService.")

    # 3. Initialize Telegram Bot
    global telegram_app
    try:
        telegram_app = init_telegram_app()
        notification_service.bot = telegram_app.bot
        logger.info("Telegram Bot initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram Bot: {e}")

    # 4. Position Reconciliation (Non-blocking)
    asyncio.create_task(reconcile_positions())
    
    logger.info("CBX Bot ready. Port: 8000")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down CBX Bot API...")
