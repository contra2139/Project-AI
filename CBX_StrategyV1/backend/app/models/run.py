from sqlalchemy import Column, String, DateTime, DECIMAL, Integer, ForeignKey, UUID, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class ResearchRun(Base):
    __tablename__ = "research_run"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_name = Column(String(100), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    strategy_config_id = Column(UUID(as_uuid=True), ForeignKey("symbol_strategy_config.strategy_config_id"), nullable=False)
    mode = Column(String(10), nullable=False) # BACKTEST, PAPER, LIVE
    status = Column(String(10), nullable=False) # RUNNING, COMPLETED, FAILED, ABORTED
    entry_model = Column(String(20), nullable=False) # FOLLOW_THROUGH, RETEST, BOTH
    side_filter = Column(String(10), nullable=False) # LONG_ONLY, SHORT_ONLY, BOTH
    data_start = Column(DateTime, nullable=False)
    data_end = Column(DateTime, nullable=False)
    run_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    run_end = Column(DateTime, nullable=True)
    git_commit = Column(String(40), nullable=False)
    
    # Aggregated results
    total_events_detected = Column(Integer, nullable=True)
    total_breakouts = Column(Integer, nullable=True)
    total_trades = Column(Integer, nullable=True)
    win_count = Column(Integer, nullable=True)
    loss_count = Column(Integer, nullable=True)
    win_rate = Column(DECIMAL(6, 4), nullable=True)
    total_pnl_r = Column(DECIMAL(10, 4), nullable=True)
    max_drawdown_r = Column(DECIMAL(10, 4), nullable=True)
    sharpe_ratio = Column(DECIMAL(8, 4), nullable=True)
    profit_factor = Column(DECIMAL(8, 4), nullable=True)
    notes = Column(Text, nullable=True)

    compression_events = relationship("CompressionEvent", back_populates="run_ref")

class WalkForwardWindow(Base):
    __tablename__ = "walk_forward_window"

    window_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wf_experiment_id = Column(UUID(as_uuid=True), nullable=False)
    symbol_id = Column(UUID(as_uuid=True), ForeignKey("symbol_registry.symbol_id"), nullable=False)
    window_index = Column(Integer, nullable=False)
    train_start = Column(DateTime, nullable=False)
    train_end = Column(DateTime, nullable=False)
    test_start = Column(DateTime, nullable=False)
    test_end = Column(DateTime, nullable=False)
    train_run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    test_run_id = Column(UUID(as_uuid=True), ForeignKey("research_run.run_id"), nullable=False)
    
    train_pnl_r = Column(DECIMAL(10, 4), nullable=True)
    test_pnl_r = Column(DECIMAL(10, 4), nullable=True)
    train_win_rate = Column(DECIMAL(6, 4), nullable=True)
    test_win_rate = Column(DECIMAL(6, 4), nullable=True)
    efficiency_ratio = Column(DECIMAL(8, 4), nullable=True)
    best_params_json = Column(Text, nullable=True) # JSON stored as text
    overfitting_flag = Column(Boolean, nullable=True)
