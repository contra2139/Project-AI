from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID, Boolean, Date
import uuid
from datetime import datetime
from app.database import Base

class SessionState(Base):
    __tablename__ = "session_state"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    date = Column(Date, nullable=False)
    equity_start_of_day = Column(DECIMAL(18, 2), nullable=False)
    current_equity = Column(DECIMAL(18, 2), nullable=False)
    current_daily_pnl_r = Column(DECIMAL(10, 4), nullable=False)
    current_daily_pnl_usd = Column(DECIMAL(18, 2), nullable=False)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    open_position_count = Column(Integer, nullable=False, default=0)
    trading_halted = Column(Boolean, nullable=False, default=False)
    halt_reason = Column(String(20), nullable=True) # DAILY_STOP, CONSECUTIVE_FAIL, MANUAL
    halt_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class EquitySnapshot(Base):
    __tablename__ = "equity_snapshot"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    time = Column(DateTime, nullable=False)
    trigger = Column(String(15), nullable=False) # TRADE_CLOSE, DAILY_OPEN, DAILY_CLOSE
    equity_usd = Column(DECIMAL(18, 2), nullable=False)
    unrealized_pnl_usd = Column(DECIMAL(18, 2), nullable=False)
    realized_pnl_usd = Column(DECIMAL(18, 2), nullable=False)
    drawdown_from_peak_pct = Column(DECIMAL(8, 4), nullable=False)
    peak_equity = Column(DECIMAL(18, 2), nullable=False)
    open_trades = Column(Integer, nullable=False)
