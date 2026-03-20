import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import ResearchRun
from app.models.trade import Trade, ExitEvent
from app.models.session import SessionState, EquitySnapshot
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig, SymbolExchangeConfig
from app.models.events import CompressionEvent, BreakoutEvent, ExpansionEvent

from app.strategy.compression_detector import CompressionDetector
from app.strategy.breakout_detector import BreakoutDetector
from app.strategy.expansion_validator import ExpansionValidator
from app.strategy.context_filter import ContextFilter
from app.strategy.risk_engine import RiskEngine
from app.strategy.entry_engine import EntryEngine
from app.strategy.trade_manager import TradeManager
from app.strategy.feature_engine import FeatureEngine
from app.backtest.simulator import FillSimulator

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    symbol_id: UUID
    strategy_config_id: UUID
    data_start: datetime
    data_end: datetime
    entry_model: str = "FOLLOW_THROUGH" # FOLLOW_THROUGH, RETEST, BOTH
    side_filter: str = "BOTH"           # LONG_ONLY, SHORT_ONLY, BOTH
    run_name: str = "Backtest Run"
    slippage_atr_pct: Decimal = Decimal("0.05")
    initial_equity: Decimal = Decimal("10000")
    taker_fee_pct: Decimal = Decimal("0.0005")

@dataclass
class BacktestRunResult:
    run_id: UUID
    total_trades: int
    win_rate: Decimal
    total_pnl_r: Decimal
    total_pnl_usd: Decimal
    max_drawdown_r: Decimal
    trades: List[Trade] = field(default_factory=list)

class MockSessionState:
    def __init__(self, initial_equity: Decimal):
        self.equity = initial_equity
        self.open_position_count = 0
        self.consecutive_failures = 0
        self.daily_pnl_r = Decimal("0")
        
    def can_trade(self, side: str, config: dict) -> bool:
        if self.open_position_count >= config.get("max_position_per_symbol", 1):
            return False
        if self.consecutive_failures >= config.get("consecutive_fail_limit", 3):
            return False
        return True

class BacktestEngine:
    def __init__(self, db_factory):
        self.db_factory = db_factory
        self.simulator = FillSimulator()
        self.compression_detector = CompressionDetector()
        self.breakout_detector = BreakoutDetector()
        self.expansion_validator = ExpansionValidator()
        self.context_filter = ContextFilter()
        self.risk_engine = RiskEngine()
        self.entry_engine = EntryEngine()
        self.trade_manager = TradeManager()
        self.feature_engine = FeatureEngine()

    async def run(self, config: BacktestConfig) -> BacktestRunResult:
        async with self.db_factory() as db:
            # 1. Setup
            run_id = await self._initialize_run(db, config)
            df_15m, df_1h, strat_config, ex_config = await self._load_data(db, config)
            strat_params = {c.name: getattr(strat_config, c.name) for c in strat_config.__table__.columns}
            print(f"DEBUG: [{config.run_name}] Strategy Config V:{strat_params.get('version', '?')}, Ratio:{strat_params.get('breakout_volume_ratio_min', '?')}, Body:{strat_params.get('breakout_body_ratio_min', '?')}")
            
            # 2. Feature Engineering (Vectorized)
            logger.info("Calculating technical features and percentiles...")
            df_15m = self.feature_engine.compute_features(df_15m, atr_period=int(strat_params.get("atr_period", 14)))
            df_15m = self.feature_engine.calculate_percentiles(df_15m, window=int(strat_params.get("atr_percentile_window", 120)))
            
            # ALSO compute for 1H data (for trend/vol context)
            df_1h = self.feature_engine.compute_features(df_1h, atr_period=14)
            
            # 3. Simulation Loop
            logger.info(f"Starting simulation loop for {len(df_15m)} bars...")
            trades, events = await self._run_simulation(df_15m, df_1h, run_id, config, strat_params, ex_config)
            
            # 3. Record Results
            result = await self._finalize_run(db, run_id, trades, events, config)
            return result

    async def _initialize_run(self, db: AsyncSession, config: BacktestConfig) -> UUID:
        run = ResearchRun(
            run_name=config.run_name,
            symbol_id=config.symbol_id,
            strategy_config_id=config.strategy_config_id,
            mode="BACKTEST",
            status="RUNNING",
            entry_model=config.entry_model,
            side_filter=config.side_filter,
            data_start=config.data_start,
            data_end=config.data_end,
            git_commit="BACKTEST_HOTFIX_V1"
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        if run.run_id is None:
            raise ValueError("Failed to initialize ResearchRun")
        return run.run_id

    async def _load_data(self, db: AsyncSession, config: BacktestConfig) -> Tuple[pd.DataFrame, pd.DataFrame, SymbolStrategyConfig, SymbolExchangeConfig]:
        # Fetch configs
        stmt_strat = select(SymbolStrategyConfig).where(SymbolStrategyConfig.strategy_config_id == config.strategy_config_id)
        res_strat = await db.execute(stmt_strat)
        strat_config = res_strat.scalar_one()

        stmt_ex = select(SymbolExchangeConfig).where(SymbolExchangeConfig.symbol_id == config.symbol_id).order_by(SymbolExchangeConfig.fetched_at.desc())
        res_ex = await db.execute(stmt_ex)
        ex_config = res_ex.scalar_one()

        # Fetch Symbol name
        stmt_sym = select(SymbolRegistry.symbol).where(SymbolRegistry.symbol_id == config.symbol_id)
        res_sym = await db.execute(stmt_sym)
        symbol_name = res_sym.scalar_one()

        # Fetch OHLCV using text query for efficiency
        # SQLite DATETIME column stores strings: '2024-03-01 07:00:00'
        start_str = (config.data_start - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        end_str = config.data_end.strftime("%Y-%m-%d %H:%M:%S")
        
        query_15m = text("SELECT timestamp, open, high, low, close, volume FROM ohlcv_15m WHERE symbol = :symbol AND timestamp >= :start AND timestamp <= :end ORDER BY timestamp ASC")
        res_15m = await db.execute(query_15m, {"symbol": symbol_name, "start": start_str, "end": end_str})
        rows_15m = res_15m.fetchall()
        print(f"DEBUG: [{symbol_name}] Fetched {len(rows_15m)} bars for 15m")
        df_15m = pd.DataFrame(rows_15m, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        # 1H data needs more history for indicators
        start_str_1h = (config.data_start - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        query_1h = text("SELECT timestamp, open, high, low, close, volume FROM ohlcv_1h WHERE symbol = :symbol AND timestamp >= :start AND timestamp <= :end ORDER BY timestamp ASC")
        res_1h = await db.execute(query_1h, {"symbol": symbol_name, "start": start_str_1h, "end": end_str})
        rows_1h = res_1h.fetchall()
        print(f"DEBUG: [{symbol_name}] Fetched {len(rows_1h)} bars for 1h")
        df_1h = pd.DataFrame(rows_1h, columns=["timestamp", "open", "high", "low", "close", "volume"])

        return df_15m, df_1h, strat_config, ex_config

    async def _run_simulation(self, df_15m: pd.DataFrame, df_1h: pd.DataFrame, run_id: UUID, config: BacktestConfig, strat_params: dict, ex_config: Any) -> Tuple[List[Trade], List[CompressionEvent]]:
        logger.info(f"Pre-calculating indicators for {len(df_15m)} bars...")
        # Ensure timestamps are datetime
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
        
        equity = config.initial_equity
        session = MockSessionState(equity)
        open_trades: List[Trade] = []
        all_trades: List[Trade] = []
        all_events: List[CompressionEvent] = []
        
        warmup = int(strat_params.get("atr_percentile_window", 120))
        idx_1h = 0
        
        for i in range(warmup, len(df_15m)):
            current_bar = df_15m.iloc[i] # KEEP as Series
            # USE SLICE of max_bars (e.g. 30) instead of full visible data for performance
            max_bars = int(strat_params.get("compression_max_bars", 24))
            # visible_data should EXCLUDE current bar for zone detection to avoid look-ahead bias
            # and allow the current bar to actually break out of the zone.
            visible_data = df_15m.iloc[max(0, i - max_bars - 5) : i] 
            
            # 1. Update existing trades
            for trade in open_trades[:]:
                if not hasattr(trade, 'hold_bars') or trade.hold_bars is None:
                    trade.hold_bars = 0
                trade.hold_bars += 1
                self.trade_manager.update_mfe_mae(trade, current_bar)
                # 1.1 Use entry_zone as fallback if no current zone (Bug 4 Fix)
                active_zone = (zone if (zone and zone.is_active) else getattr(trade, 'entry_zone', None)) or trade.entry_zone
                
                # 1.2 Calculate new trailing stop if partial exit done
                if trade.partial_exit_done:
                    # Get recent bars (last 2)
                    lookback = 5 # buffer
                    start_idx = max(0, i - lookback)
                    recent_bars_data = df_15m.iloc[start_idx : i + 1].to_dict('records')
                    new_ts = self.trade_manager.get_trailing_stop(trade, recent_bars_data, active_zone, strat_params)
                    if new_ts:
                        trade.trailing_stop_price = new_ts

                action = self.trade_manager.update(trade, current_bar, active_zone, strat_params)
                
                if action.action_type == "CLOSE_FULL":
                    hit, price = self.simulator.simulate_stop_hit(trade.side, Decimal(str(action.price)) if hasattr(action, 'price') else Decimal(str(action.close_price)), current_bar)
                    real_exit_price = price if hit else Decimal(str(current_bar["close"]))
                    print(f"!!! TRADE CLOSED !!! {trade.symbol_id} at {current_bar['timestamp']} Reason: {action.reason}")
                    self._close_trade(trade, real_exit_price, action.reason, current_bar["timestamp"], config.taker_fee_pct)
                    session.open_position_count -= 1
                    open_trades.remove(trade)
                    all_trades.append(trade)
                elif action.action_type == "CLOSE_PARTIAL":
                    hit, price = self.simulator.simulate_partial_fill(trade.side, Decimal(str(action.close_price)), current_bar)
                    if hit:
                        print(f"!!! PARTIAL EXIT !!! {trade.symbol_id} at {current_bar['timestamp']}")
                        trade.partial_exit_done = True
            
            # 1. Update 1H context index (Optimized)
            while idx_1h < len(df_1h) and df_1h.iloc[idx_1h]['timestamp'] <= current_bar['timestamp']:
                idx_1h += 1
            matching_1h = df_1h.iloc[max(0, idx_1h - 10) : idx_1h]
            if matching_1h.empty: continue
            
            # 3. Detection
            try:
                zone = self.compression_detector.detect(visible_data, run_id, config.symbol_id, strat_params)
            except Exception as e:
                logger.error(f"Error in compression_detector.detect at index {i}: {e}")
                raise e
                
            if not zone or not zone.is_active: continue
            
            # 4. Breakout
            try:
                breakout = self.breakout_detector.detect(current_bar, zone, current_bar, strat_params)
            except Exception as e:
                logger.error(f"Error in breakout_detector.detect at index {i}: {e}")
                raise e
                
            if not breakout.is_valid: continue
            
            # Side Filter check
            if config.side_filter == "LONG_ONLY" and breakout.side == "SHORT": continue
            if config.side_filter == "SHORT_ONLY" and breakout.side == "LONG": continue
            
            # Create BreakoutEvent Model
            breakout_event = BreakoutEvent(
                breakout_id=uuid4(),
                event_id=zone.event_id,
                time=current_bar["timestamp"],
                side=breakout.side,
                open=Decimal(str(current_bar["open"])),
                high=Decimal(str(current_bar["high"])),
                low=Decimal(str(current_bar["low"])),
                close=Decimal(str(current_bar["close"])),
                breakout_price_level=breakout.breakout_price_level,
                breakout_distance=abs(Decimal(str(current_bar["close"])) - breakout.breakout_price_level),
                breakout_distance_atr=breakout.breakout_distance_atr,
                bar_size_atr=breakout.bar_size_atr,
                body_to_range=breakout.body_to_range,
                close_position_in_candle=breakout.close_position_in_candle,
                vol_ratio=breakout.vol_ratio,
                vol_percentile=breakout.vol_percentile,
                is_wick_dominant=breakout.is_wick_dominant,
                is_valid=True
            )
            
            # 5. Context Trend Check
            try:
                ctx = self.context_filter.check(matching_1h, breakout.side, breakout, strat_params)
            except Exception as e:
                logger.error(f"Error in context_filter.check at index {i}: {e}")
                raise e
            if not ctx.allowed: continue

            # 6. Expansion
            next_bars = df_15m.iloc[i+1 : i+1 + int(strat_params.get("expansion_lookforward_bars", 3))].to_dict('records')
            try:
                expansion = self.expansion_validator.validate(breakout, next_bars, zone, strat_params)
                if expansion:
                    expansion.is_active = True # Ensure expansion event is marked active
            except Exception as e:
                logger.error(f"Error in expansion_validator.validate for {config.symbol_id}: {e}")
                logger.error(f"breakout.breakout_bar: {breakout.breakout_bar if breakout else 'None'}")
                raise e
            if not expansion or not expansion.is_confirmed: continue
            
            # Create ExpansionEvent Model
            expansion_event = ExpansionEvent(
                expansion_id=uuid4(),
                breakout_id=breakout_event.breakout_id,
                is_confirmed=True,
                confirmation_bar_index=expansion.confirmation_bar_index,
                confirmation_time=expansion.confirmation_time,
                max_extension_price=expansion.max_extension_price,
                max_extension_atr=expansion.max_extension_atr,
                reentry_occurred=expansion.reentry_occurred,
                reentry_depth_pct=expansion.reentry_depth_pct,
                body_loss_pct=expansion.body_loss_pct,
                higher_high_formed=expansion.higher_high_formed,
                lower_low_formed=expansion.lower_low_formed
            )
            
            # 7. Risk & Entry
            try:
                sl_price = self.risk_engine.calculate_stop_loss(breakout.side, zone, breakout.breakout_bar, strat_params)
            except Exception as e:
                logger.error(f"Error calculating stop loss: {e}")
                logger.error(f"breakout_bar: {breakout.breakout_bar if breakout else 'None'}")
                raise e
            
            entry_price = Decimal(str(next_bars[0]['open'])) if next_bars else Decimal(str(current_bar['close']))
            print(f"entry_price: {entry_price}")
            print(f"breakout.side: {breakout.side}")
            print(f"zone.atr_value: {zone.atr_value}")
            print(f"config.slippage_atr_pct: {config.slippage_atr_pct}")
            
            if not session.can_trade(breakout.side, strat_params): continue
            
            try:
                entry_bar = df_15m.iloc[i + expansion.confirmation_bar_index + 1].to_dict()
                fill_price = self.simulator.simulate_entry_fill(entry_bar, breakout.side, zone.atr_value, config.slippage_atr_pct)
                sl_price = self.risk_engine.calculate_stop_loss(breakout.side, zone, breakout.breakout_bar, strat_params)
                
                print(f"!!! TRADE FOUND !!! {config.symbol_id} at {current_bar['timestamp']}")
                print(f"  Side: {breakout.side}, Entry: {fill_price}, SL: {sl_price}")
                
                risk_r_price = abs(fill_price - sl_price)
                
                # Dynamic Position Sizing
                risk_pct = Decimal(str(strat_params.get('risk_per_trade_pct', 0.25))) / Decimal("100")
                risk_amount_usd = config.initial_equity * risk_pct
                
                if risk_r_price > 0:
                    pos_size = risk_amount_usd / risk_r_price
                else:
                    pos_size = Decimal("0.1") # Fallback
                
                trade = Trade(
                    trade_id=uuid4(),
                    expansion_id=expansion_event.expansion_id,
                    run_id=run_id,
                    symbol_id=config.symbol_id,
                    side=breakout.side,
                    entry_model=config.entry_model,
                    entry_time=entry_bar["timestamp"],
                    entry_price=fill_price,
                    stop_loss_price=sl_price,
                    tp1_price=fill_price + risk_r_price if breakout.side == "LONG" else fill_price - risk_r_price,
                    initial_risk_r_price=risk_r_price,
                    position_size=pos_size,
                    position_size_usd=pos_size * fill_price,
                    risk_amount_usd=pos_size * risk_r_price,
                    status="OPEN"
                )
                
                trade.is_active = True
                trade.hold_bars = 0
                trade.MFE_r = Decimal("0")
                trade.MAE_r = Decimal("0")
                trade.trailing_stop_price = None
                trade.partial_exit_done = False
                
                trade.entry_zone = zone # Bug 4 Fix
                trade._zone = zone
                
                # Bug 3 Fix: Stop Loss Validation
                if trade.stop_loss_price is None or trade.stop_loss_price <= 0:
                    logger.error(f"!!! INVALID STOP LOSS !!! Trade for {config.symbol_id} skipped. SL: {trade.stop_loss_price}")
                    continue

                open_trades.append(trade)
                session.open_position_count += 1
                
                all_events.append(zone)
                all_events.append(breakout_event)
                all_events.append(expansion_event)
            except Exception as e:
                print(f"!!! ERROR CREATING TRADE !!!: {e}")
                continue

        # Force Close End
        last_bar = df_15m.iloc[-1].to_dict()
        for trade in open_trades:
            self._close_trade(trade, Decimal(str(last_bar["close"])), "FORCE_CLOSE_END_OF_DATA", last_bar["timestamp"], config.taker_fee_pct)
            all_trades.append(trade)
        
        return all_trades, all_events

    def _close_trade(self, trade: Trade, exit_price: Decimal, reason: str, exit_time: datetime, fee_pct: Decimal):
        trade.status = "CLOSED"
        trade.avg_exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_model = reason
        
        # PnL R
        risk_dist = trade.initial_risk_r_price
        if risk_dist and risk_dist > 0:
            if trade.side == "LONG":
                raw_pnl = (exit_price - trade.entry_price)
            else: # SHORT
                raw_pnl = (trade.entry_price - exit_price)
            trade.total_pnl_r = Decimal(str(raw_pnl / risk_dist))
            
            # USD PnL (Net)
            gross_pnl_usd = raw_pnl * trade.position_size
            entry_fee = trade.position_size * trade.entry_price * fee_pct
            exit_fee = trade.position_size * exit_price * fee_pct
            total_fees = entry_fee + exit_fee
            
            trade.total_pnl_usd = Decimal(str(gross_pnl_usd - total_fees))
            trade.total_fees_usd = Decimal(str(total_fees))
            
            print(f"[FEE DEBUG] Symbol={trade.symbol_id}")
            print(f"  Entry: qty={trade.position_size:.4f}, price={trade.entry_price:.2f}")
            print(f"  Entry notional={trade.position_size * trade.entry_price:.2f}")
            print(f"  Entry fee={entry_fee:.4f}")
            print(f"  Exit:  qty={trade.position_size:.4f}, price={exit_price:.2f}")
            print(f"  Exit notional={trade.position_size * exit_price:.2f}")
            print(f"  Exit fee={exit_fee:.4f}")
            print(f"  Total fees={total_fees:.4f}")
            print(f"  Gross PnL={gross_pnl_usd:.4f}")
            print(f"  Net PnL={trade.total_pnl_usd:.4f}")

    async def _finalize_run(self, db: AsyncSession, run_id: UUID, trades: List[Trade], events: List[CompressionEvent], config: BacktestConfig) -> BacktestRunResult:
        # Save Trades and Events
        for event in events:
            db.add(event)
        for trade in trades:
            db.add(trade)
            
        # Summary
        wins = [t for t in trades if (t.total_pnl_r or 0) > 0]
        total_r = sum(t.total_pnl_r or 0 for t in trades)
        
        # Update Run
        stmt = update(ResearchRun).where(ResearchRun.run_id == run_id).values(
            status="COMPLETED",
            run_end=datetime.utcnow(),
            total_trades=len(trades),
            win_count=len(wins),
            loss_count=len(trades) - len(wins),
            win_rate=Decimal(str(len(wins)/len(trades))) if trades else Decimal("0"),
            total_pnl_r=Decimal(str(total_r))
        )
        await db.execute(stmt)
        await db.commit()
        
        win_rate = Decimal(str(len(wins)/len(trades))) if trades else Decimal("0")
        return BacktestRunResult(
            run_id=run_id,
            total_trades=len(trades),
            win_rate=win_rate,
            total_pnl_r=total_r,
            total_pnl_usd=Decimal("0"), # Placeholder
            max_drawdown_r=Decimal("0"),  # Placeholder
            trades=trades
        )
