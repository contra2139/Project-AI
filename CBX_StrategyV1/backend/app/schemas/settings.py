from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

class BotModeUpdate(BaseModel):
    mode: str = Field(pattern="^(auto|manual)$")

class BotModeRead(BaseModel):
    mode: str
    updated_at: str

class RiskSettingsUpdate(BaseModel):
    risk_per_trade_pct: Decimal = Field(ge=0.001, le=0.05)
    max_positions_portfolio: int = Field(ge=1, le=50)
    daily_stop_r: Decimal = Field(ge=0.1)

class NotificationSettingsUpdate(BaseModel):
    notify_on_signal: bool
    notify_on_entry: bool
    notify_on_exit: bool
    notify_daily_summary: bool

class AllSettingsRead(BaseModel):
    mode: str
    risk: RiskSettingsUpdate
    notifications: NotificationSettingsUpdate
