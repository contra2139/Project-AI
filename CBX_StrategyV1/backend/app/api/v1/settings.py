from fastapi import APIRouter, Depends, HTTPException, status
import json
from datetime import datetime
from typing import Any

from app.api.dependencies import get_current_user, get_redis
from app.schemas.settings import BotModeUpdate, BotModeRead, RiskSettingsUpdate, NotificationSettingsUpdate, AllSettingsRead

router = APIRouter()

@router.get("/", response_model=AllSettingsRead)
async def get_all_settings(
    current_user: str = Depends(get_current_user),
    redis=Depends(get_redis)
):
    # Load from Redis with defaults
    mode = await redis.get("bot:mode")
    risk_raw = await redis.get("bot:risk_settings")
    notif_raw = await redis.get("bot:notification_settings")
    
    return {
        "mode": (mode.decode() if mode else "manual"),
        "risk": json.loads(risk_raw) if risk_raw else {
            "risk_per_trade_pct": 0.01,
            "max_positions_portfolio": 5,
            "daily_stop_r": 3.0
        },
        "notifications": json.loads(notif_raw) if notif_raw else {
            "notify_on_signal": True,
            "notify_on_entry": True,
            "notify_on_exit": True,
            "notify_daily_summary": True
        }
    }

@router.patch("/mode", response_model=BotModeRead)
async def update_mode(
    data: BotModeUpdate,
    current_user: str = Depends(get_current_user),
    redis=Depends(get_redis)
):
    await redis.set("bot:mode", data.mode)
    updated_at = datetime.utcnow().isoformat()
    await redis.set("bot:mode_updated_at", updated_at)
    
    return {"mode": data.mode, "updated_at": updated_at}

@router.patch("/risk")
async def update_risk(
    data: RiskSettingsUpdate,
    current_user: str = Depends(get_current_user),
    redis=Depends(get_redis)
):
    # Serializing Decimal to float for JSON
    await redis.set("bot:risk_settings", json.dumps(data.model_dump(), default=str))
    return data

@router.patch("/notifications")
async def update_notifications(
    data: NotificationSettingsUpdate,
    current_user: str = Depends(get_current_user),
    redis=Depends(get_redis)
):
    await redis.set("bot:notification_settings", json.dumps(data.model_dump()))
    return data
