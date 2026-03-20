from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class ResearchRunRead(BaseModel):
    run_id: UUID
    run_name: str
    symbol_id: UUID
    strategy_config_id: UUID
    mode: str
    status: str
    entry_model: str
    side_filter: str
    data_start: datetime
    data_end: datetime
    run_start: datetime
    run_end: Optional[datetime] = None
    
    # Optional metrics
    total_trades: Optional[int] = None
    win_rate: Optional[Decimal] = None
    total_pnl_r: Optional[Decimal] = None
    max_drawdown_r: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)

class BacktestConfigSchema(BaseModel):
    symbol_id: UUID
    strategy_config_id: UUID
    data_start: datetime
    data_end: datetime
    run_name: str
    side_filter: str = "BOTH"
    entry_model: str = "FOLLOW_THROUGH"
    initial_equity: Decimal = Decimal("10000")
