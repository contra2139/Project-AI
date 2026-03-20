from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID, Boolean
import uuid
from app.database import Base

class PercentileCache(Base):
    __tablename__ = "percentile_cache"

    cache_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    bar_time = Column(DateTime, nullable=False)
    timeframe = Column(String(5), nullable=False)
    window_size = Column(Integer, nullable=False)
    is_expanding = Column(Boolean, nullable=False)
    atr_normalized_value = Column(DECIMAL(12, 8), nullable=False)
    atr_percentile = Column(DECIMAL(6, 4), nullable=False)
    range_value = Column(DECIMAL(12, 8), nullable=False)
    range_percentile = Column(DECIMAL(6, 4), nullable=False)
    bb_width_value = Column(DECIMAL(12, 8), nullable=False)
    bb_width_percentile = Column(DECIMAL(6, 4), nullable=False)
    volume_value = Column(DECIMAL(20, 2), nullable=False)
    volume_percentile = Column(DECIMAL(6, 4), nullable=False)

class MarketRegimeLog(Base):
    __tablename__ = "market_regime_log"

    regime_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    bar_time = Column(DateTime, nullable=False)
    realized_vol_24h = Column(DECIMAL(10, 6), nullable=False)
    realized_vol_1h = Column(DECIMAL(10, 6), nullable=False)
    vol_percentile_90d = Column(DECIMAL(6, 4), nullable=False)
    regime = Column(String(15), nullable=False) # NORMAL, LOW_VOL, HIGH_VOL, SHOCK
    regime_reason = Column(String(100), nullable=True)
    is_tradeable = Column(Boolean, nullable=False)
    block_reason = Column(String(100), nullable=True)
    ema50_1h = Column(DECIMAL(18, 6), nullable=False)
    ema50_slope = Column(DECIMAL(10, 6), nullable=False)
    close_1h = Column(DECIMAL(18, 6), nullable=False)
    close_vs_ema50_pct = Column(DECIMAL(8, 4), nullable=False)
