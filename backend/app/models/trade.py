from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID, Boolean
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Trade(Base):
    __tablename__ = "trade"

    trade_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expansion_id = Column(UUID(as_uuid=True), ForeignKey("expansion_event.expansion_id"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    side = Column(String(5), nullable=False) # LONG, SHORT
    entry_model = Column(String(20), nullable=False) # FOLLOW_THROUGH, RETEST
    exit_model = Column(String(20), nullable=True) # FIXED_R, TIME_STOP, STRUCTURE_FAIL, TRAILING
    entry_time = Column(DateTime, nullable=False, index=True)
    entry_price = Column(DECIMAL(18, 6), nullable=False)
    stop_loss_price = Column(DECIMAL(18, 6), nullable=False)
    tp1_price = Column(DECIMAL(18, 6), nullable=False)
    initial_risk_r_price = Column(DECIMAL(18, 6), nullable=False)
    position_size = Column(DECIMAL(18, 6), nullable=False)
    position_size_usd = Column(DECIMAL(18, 2), nullable=False)
    risk_amount_usd = Column(DECIMAL(18, 2), nullable=False)
    exit_time = Column(DateTime, nullable=True, index=True)
    avg_exit_price = Column(DECIMAL(18, 6), nullable=True)
    hold_bars = Column(Integer, nullable=True)
    MFE_r = Column(DECIMAL(10, 4), nullable=True)
    MAE_r = Column(DECIMAL(10, 4), nullable=True)
    MFE_price = Column(DECIMAL(18, 6), nullable=True)
    MAE_price = Column(DECIMAL(18, 6), nullable=True)
    partial_exit_done = Column(Boolean, nullable=False, default=False)
    trailing_stop_price = Column(DECIMAL(18, 6), nullable=True)
    gross_pnl_usd = Column(DECIMAL(18, 2), nullable=True)
    total_fees_usd = Column(DECIMAL(18, 2), nullable=True)
    slippage_usd = Column(DECIMAL(18, 2), nullable=True)
    net_pnl_usd = Column(DECIMAL(18, 2), nullable=True)
    total_pnl_usd = Column(DECIMAL(18, 2), nullable=True)
    total_pnl_r = Column(DECIMAL(10, 4), nullable=True)
    status = Column(String(10), nullable=False) # OPEN, CLOSED, CANCELLED
    cancel_reason = Column(String(200), nullable=True)

    expansion_ref = relationship("ExpansionEvent", back_populates="trades")
    exit_events = relationship("ExitEvent", back_populates="trade_ref")
    order_logs = relationship("OrderLog", back_populates="trade_ref")

class ExitEvent(Base):
    __tablename__ = "exit_event"

    exit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trade.trade_id"), nullable=False)
    exit_sequence = Column(Integer, nullable=False)
    time = Column(DateTime, nullable=False, index=True)
    exit_type = Column(String(20), nullable=False) # PARTIAL_1R, TRAILING, STOP_LOSS, TIME_STOP, STRUCTURE_FAIL, MANUAL
    trigger_price = Column(DECIMAL(18, 6), nullable=False)
    fill_price = Column(DECIMAL(18, 6), nullable=False)
    size_closed = Column(DECIMAL(18, 6), nullable=False)
    remaining_size = Column(DECIMAL(18, 6), nullable=False)
    pnl_realized_r = Column(DECIMAL(10, 4), nullable=False)
    pnl_realized_usd = Column(DECIMAL(18, 2), nullable=False)
    cumulative_pnl_r = Column(DECIMAL(10, 4), nullable=False)
    fee_usd = Column(DECIMAL(18, 2), nullable=False)
    trailing_stop_level = Column(DECIMAL(18, 6), nullable=True)

    trade_ref = relationship("Trade", back_populates="exit_events")

class OrderLog(Base):
    __tablename__ = "order_log"

    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exchange_order_id = Column(String(50), nullable=True)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trade.trade_id"), nullable=False)
    time_sent = Column(DateTime, nullable=False)
    time_filled = Column(DateTime, nullable=True)
    order_type = Column(String(15), nullable=False) # MARKET, LIMIT, STOP_MARKET
    side = Column(String(5), nullable=False) # BUY, SELL
    intent = Column(String(15), nullable=False) # ENTRY, STOP_LOSS, TAKE_PROFIT, TRAILING_STOP
    requested_price = Column(DECIMAL(18, 6), nullable=True)
    filled_price = Column(DECIMAL(18, 6), nullable=True)
    requested_qty = Column(DECIMAL(18, 6), nullable=False)
    filled_qty = Column(DECIMAL(18, 6), nullable=True)
    status = Column(String(10), nullable=False) # PENDING, FILLED, CANCELLED, REJECTED
    reject_reason = Column(String(200), nullable=True)
    latency_ms = Column(Integer, nullable=True)

    trade_ref = relationship("Trade", back_populates="order_logs")
