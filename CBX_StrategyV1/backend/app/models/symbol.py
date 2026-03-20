from sqlalchemy import Column, String, Boolean, DateTime, DECIMAL, Integer, ForeignKey, Text, JSON, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class SymbolRegistry(Base):
    __tablename__ = "symbol_registry"

    symbol_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), unique=True, nullable=False)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    exchange = Column(String(20), nullable=False)
    contract_type = Column(String(10), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_in_universe = Column(Boolean, nullable=False, default=False)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    deactivated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    exchange_configs = relationship("SymbolExchangeConfig", back_populates="symbol_ref")
    strategy_configs = relationship("SymbolStrategyConfig", back_populates="symbol_ref")

class SymbolExchangeConfig(Base):
    __tablename__ = "symbol_exchange_config"

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    lot_size_step = Column(DECIMAL(18, 8), nullable=False)
    min_qty = Column(DECIMAL(18, 8), nullable=False)
    max_qty = Column(DECIMAL(18, 8), nullable=True)
    min_notional = Column(DECIMAL(18, 2), nullable=False)
    price_tick_size = Column(DECIMAL(18, 8), nullable=False)
    maker_fee_pct = Column(DECIMAL(8, 6), nullable=False)
    taker_fee_pct = Column(DECIMAL(8, 6), nullable=False)
    default_leverage = Column(Integer, nullable=False)
    max_leverage = Column(Integer, nullable=False)
    margin_type = Column(String(10), nullable=False)
    effective_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)
    source = Column(String(20), nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    symbol_ref = relationship("SymbolRegistry", back_populates="exchange_configs")

class SymbolStrategyConfig(Base):
    __tablename__ = "symbol_strategy_config"

    strategy_config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    name = Column(String(100), nullable=True) # Optional descriptive name
    version = Column(Integer, nullable=False)
    is_current = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_by = Column(String(50), nullable=False)
    based_on_version = Column(Integer, nullable=True)
    change_reason = Column(Text, nullable=True)

    # Compression parameters
    atr_period = Column(Integer, nullable=False, default=14)
    atr_percentile_window = Column(Integer, nullable=False, default=120)
    atr_percentile_threshold = Column(DECIMAL(5, 2), nullable=False, default=20.0)
    range_bars = Column(Integer, nullable=False, default=12)
    range_percentile_threshold = Column(DECIMAL(5, 2), nullable=False, default=20.0)
    bb_period = Column(Integer, nullable=False, default=20)
    bb_std = Column(DECIMAL(4, 2), nullable=False, default=2.0)
    bb_width_percentile_threshold = Column(DECIMAL(5, 2), nullable=False, default=20.0)
    volume_percentile_threshold = Column(DECIMAL(5, 2), nullable=False, default=60.0)
    compression_min_bars = Column(Integer, nullable=False, default=8)
    compression_max_bars = Column(Integer, nullable=False, default=24)
    min_conditions_met = Column(Integer, nullable=False, default=3)

    # Breakout parameters
    breakout_distance_min_atr = Column(DECIMAL(5, 3), nullable=False, default=0.20)
    breakout_body_ratio_min = Column(DECIMAL(5, 3), nullable=False, default=0.60)
    breakout_close_position_long = Column(DECIMAL(5, 3), nullable=False, default=0.75)
    breakout_close_position_short = Column(DECIMAL(5, 3), nullable=False, default=0.25)
    breakout_volume_ratio_min = Column(DECIMAL(5, 3), nullable=False, default=1.30)
    breakout_volume_percentile_min = Column(DECIMAL(5, 2), nullable=False, default=70.0)
    breakout_bar_size_max_atr = Column(DECIMAL(5, 2), nullable=False, default=2.50)
    false_break_limit = Column(Integer, nullable=False, default=2)

    # Expansion parameters
    expansion_lookforward_bars = Column(Integer, nullable=False, default=3)
    expansion_body_loss_max_pct = Column(DECIMAL(5, 2), nullable=False, default=50.0)

    # Entry parameters
    retest_max_bars = Column(Integer, nullable=False, default=3)

    # Stop loss parameters
    stop_loss_atr_buffer = Column(DECIMAL(5, 3), nullable=False, default=0.25)
    entry_retest_buffer_atr = Column(DECIMAL(5, 3), nullable=False, default=0.05)

    # Exit parameters
    partial_exit_r_level = Column(DECIMAL(5, 2), nullable=False, default=1.0)
    partial_exit_pct = Column(DECIMAL(5, 2), nullable=False, default=50.0)
    time_stop_bars = Column(Integer, nullable=False, default=8)

    # Context filter parameters
    ema_period_context = Column(Integer, nullable=False, default=50)
    context_timeframe = Column(String(5), nullable=False, default="1h")
    execution_timeframe = Column(String(5), nullable=False, default="15m")
    
    # New V7 Context Filters
    long_min_ema_slope = Column(DECIMAL(10, 6), nullable=False, default=0.0003)
    long_min_price_vs_ema = Column(DECIMAL(10, 6), nullable=False, default=0.005)
    short_max_ema_slope = Column(DECIMAL(10, 6), nullable=False, default=-0.0003)
    short_max_price_vs_ema = Column(DECIMAL(10, 6), nullable=False, default=-0.005)

    # Risk parameters
    risk_per_trade_pct = Column(DECIMAL(6, 4), nullable=False, default=0.25)
    max_position_per_symbol = Column(Integer, nullable=False, default=1)
    trailing_atr_multiplier = Column(DECIMAL(5, 2), nullable=False, default=1.5)

    symbol_ref = relationship("SymbolRegistry", back_populates="strategy_configs")

class StrategyVersionHistory(Base):
    __tablename__ = "strategy_version_history"

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    from_version = Column(Integer, nullable=False)
    to_version = Column(Integer, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    changed_by = Column(String(50), nullable=False)
    params_diff = Column(JSON, nullable=False)
    reason = Column(Text, nullable=True)
    backtest_result_before = Column(JSON, nullable=True)
    backtest_result_after = Column(JSON, nullable=True)
