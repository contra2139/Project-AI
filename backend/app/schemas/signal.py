from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class SignalNotificationDetailed(BaseModel):
    signal_id: UUID
    symbol_id: UUID
    time: datetime
    side: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    ai_score_v1: Decimal
    quality_score: Decimal
    
    # Nested event data
    compression_id: UUID
    breakout_id: UUID
    expansion_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

class SignalSummary(BaseModel):
    signal_id: UUID
    symbol: str
    side: str
    time: datetime
    price: Decimal
    quality_score: Decimal
