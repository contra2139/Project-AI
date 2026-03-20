from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class TradeRead(BaseModel):
    trade_id: UUID
    run_id: UUID
    symbol_id: UUID
    side: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    size: Decimal
    status: str
    pnl_r: Optional[Decimal] = None
    net_pnl_usd: Optional[Decimal] = None
    total_fees_usd: Decimal
    unrealized_pnl_r: Optional[Decimal] = None # For OPEN trades
    
    model_config = ConfigDict(from_attributes=True)

class ExitEventRead(BaseModel):
    exit_event_id: UUID
    trade_id: UUID
    time: datetime
    exit_type: str
    price: Decimal
    size_pct: Decimal
    raw_pnl_r: Decimal
    is_final: bool
    
    model_config = ConfigDict(from_attributes=True)
