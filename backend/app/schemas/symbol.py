from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class SymbolRegistryBase(BaseModel):
    symbol: str
    exchange: str = "BINANCE"
    is_active: bool = True
    is_in_universe: bool = True

class SymbolRegistryCreate(SymbolRegistryBase):
    pass

class SymbolRegistryRead(SymbolRegistryBase):
    symbol_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SymbolStrategyConfigBase(BaseModel):
    timeframe: str = "5m"
    min_volume_24h_usd: Decimal
    min_atr_pct: Decimal
    max_spread_pct: Decimal
    is_current: bool = True

class SymbolStrategyConfigCreate(SymbolStrategyConfigBase):
    pass

class SymbolStrategyConfigRead(SymbolStrategyConfigBase):
    strategy_config_id: UUID
    symbol_id: UUID
    version: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
