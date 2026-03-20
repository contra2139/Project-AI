from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID
import uuid
from app.database import Base

class FilterLog(Base):
    __tablename__ = "filter_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("compression_event.event_id"), nullable=True)
    breakout_id = Column(UUID(as_uuid=True), ForeignKey("breakout_event.breakout_id"), nullable=True)
    expansion_id = Column(UUID(as_uuid=True), ForeignKey("expansion_event.expansion_id"), nullable=True)
    stage = Column(String(15), nullable=False) # COMPRESSION, BREAKOUT, EXPANSION, ENTRY
    filter_name = Column(String(50), nullable=False)
    value_at_time = Column(DECIMAL(12, 6), nullable=False)
    threshold = Column(DECIMAL(12, 6), nullable=False)
    decision = Column(String(10), nullable=False) # REJECTED, PASSED
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    time = Column(DateTime, nullable=False)

class ContextFilterLog(Base):
    __tablename__ = "context_filter_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("compression_event.event_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    time = Column(DateTime, nullable=False)
    filter_type = Column(String(20), nullable=False) # EMA50_DIRECTION, VOLATILITY_STATE
    attempted_side = Column(String(5), nullable=False) # LONG, SHORT
    ema50_1h = Column(DECIMAL(18, 6), nullable=False)
    close_1h = Column(DECIMAL(18, 6), nullable=False)
    ema50_slope = Column(DECIMAL(10, 6), nullable=False)
    vol_state = Column(String(10), nullable=False) # NORMAL, LOW_VOL, SHOCK
    realized_vol = Column(DECIMAL(10, 6), nullable=False)
    decision = Column(String(10), nullable=False) # ALLOWED, BLOCKED
    block_reason = Column(String(200), nullable=True)
