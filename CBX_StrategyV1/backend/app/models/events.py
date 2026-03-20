from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID, Boolean
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class CompressionEvent(Base):
    __tablename__ = "compression_event"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    timeframe = Column(String(5), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    bar_count = Column(Integer, nullable=False)
    high = Column(DECIMAL(18, 6), nullable=False)
    low = Column(DECIMAL(18, 6), nullable=False)
    width_pct = Column(DECIMAL(8, 4), nullable=False)
    width_atr_ratio = Column(DECIMAL(8, 4), nullable=False)
    atr_value = Column(DECIMAL(18, 6), nullable=False)
    atr_percentile = Column(DECIMAL(6, 4), nullable=False)
    range_percentile = Column(DECIMAL(6, 4), nullable=False)
    bb_width_percentile = Column(DECIMAL(6, 4), nullable=False)
    vol_percentile = Column(DECIMAL(6, 4), nullable=False)
    conditions_met = Column(Integer, nullable=False)
    false_break_count = Column(Integer, nullable=False, default=0)
    quality_score = Column(DECIMAL(6, 4), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_valid = Column(Boolean, nullable=False, default=True)
    invalid_reason = Column(String(200), nullable=True)

    run_ref = relationship("ResearchRun", back_populates="compression_events")
    breakout_events = relationship("BreakoutEvent", back_populates="compression_ref")
    feature_snapshots = relationship("FeatureSnapshot", back_populates="event_ref")

class BreakoutEvent(Base):
    __tablename__ = "breakout_event"

    breakout_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("compression_event.event_id"), nullable=False)
    time = Column(DateTime, nullable=False, index=True)
    side = Column(String(5), nullable=False) # LONG, SHORT
    open = Column(DECIMAL(18, 6), nullable=False)
    high = Column(DECIMAL(18, 6), nullable=False)
    low = Column(DECIMAL(18, 6), nullable=False)
    close = Column(DECIMAL(18, 6), nullable=False)
    breakout_price_level = Column(DECIMAL(18, 6), nullable=False)
    breakout_distance = Column(DECIMAL(18, 6), nullable=False)
    breakout_distance_atr = Column(DECIMAL(8, 4), nullable=False)
    bar_size_atr = Column(DECIMAL(8, 4), nullable=False)
    body_to_range = Column(DECIMAL(6, 4), nullable=False)
    close_position_in_candle = Column(DECIMAL(6, 4), nullable=False)
    vol_ratio = Column(DECIMAL(8, 4), nullable=False)
    vol_percentile = Column(DECIMAL(6, 4), nullable=False)
    is_wick_dominant = Column(Boolean, nullable=False)
    is_valid = Column(Boolean, nullable=False, default=True)
    invalid_reason = Column(String(200), nullable=True)

    compression_ref = relationship("CompressionEvent", back_populates="breakout_events")
    expansion_events = relationship("ExpansionEvent", back_populates="breakout_ref")

class ExpansionEvent(Base):
    __tablename__ = "expansion_event"

    expansion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    breakout_id = Column(UUID(as_uuid=True), ForeignKey("breakout_event.breakout_id"), nullable=False)
    is_confirmed = Column(Boolean, nullable=False)
    rejection_reason = Column(String(200), nullable=True)
    confirmation_bar_index = Column(Integer, nullable=True)
    confirmation_time = Column(DateTime, nullable=True, index=True)
    max_extension_atr = Column(DECIMAL(8, 4), nullable=True)
    max_extension_price = Column(DECIMAL(18, 6), nullable=True)
    reentry_occurred = Column(Boolean, nullable=False)
    reentry_depth_pct = Column(DECIMAL(8, 4), nullable=True)
    body_loss_pct = Column(DECIMAL(8, 4), nullable=False)
    higher_high_formed = Column(Boolean, nullable=True)
    lower_low_formed = Column(Boolean, nullable=True)

    breakout_ref = relationship("BreakoutEvent", back_populates="expansion_events")
    trades = relationship("Trade", back_populates="expansion_ref")

class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshot"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("compression_event.event_id"), nullable=False)
    bar_time = Column(DateTime, nullable=False, index=True)
    close = Column(DECIMAL(18, 6), nullable=False)
    atr_14 = Column(DECIMAL(18, 6), nullable=False)
    atr_normalized = Column(DECIMAL(12, 8), nullable=False)
    atr_percentile = Column(DECIMAL(6, 4), nullable=False)
    range_12 = Column(DECIMAL(12, 8), nullable=False)
    range_percentile = Column(DECIMAL(6, 4), nullable=False)
    bb_width = Column(DECIMAL(12, 8), nullable=False)
    bb_width_percentile = Column(DECIMAL(6, 4), nullable=False)
    volume_sma20 = Column(DECIMAL(20, 2), nullable=False)
    volume_ratio = Column(DECIMAL(10, 4), nullable=False)
    volume_percentile = Column(DECIMAL(6, 4), nullable=False)
    ema50_1h = Column(DECIMAL(18, 6), nullable=False)
    ema50_slope = Column(DECIMAL(10, 6), nullable=False)
    realized_vol_1h = Column(DECIMAL(10, 6), nullable=False)
    close_vs_ema50_pct = Column(DECIMAL(8, 4), nullable=False)

    event_ref = relationship("CompressionEvent", back_populates="feature_snapshots")
