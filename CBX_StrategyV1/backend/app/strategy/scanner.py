import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Literal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.trade import Trade
from app.models.session import SessionState
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig, SymbolExchangeConfig
from app.models.events import CompressionEvent

from app.strategy.compression_detector import CompressionDetector
from app.strategy.breakout_detector import BreakoutDetector
from app.strategy.expansion_validator import ExpansionValidator
from app.strategy.context_filter import ContextFilter
from app.strategy.risk_engine import RiskEngine
from app.strategy.entry_engine import EntryEngine
from app.strategy.trade_manager import TradeManager

logger = logging.getLogger(__name__)

# --- Interfaces for external services ---

class DataFetcher:
    """Interface for fetching market data."""
    async def get_klines(self, symbol: str, interval: str, limit: int = 500):
        raise NotImplementedError

class OrderExecutor:
    """Interface for executing orders on exchange."""
    async def place_market_order(self, symbol: str, side: str, qty: Decimal):
        raise NotImplementedError
    async def get_account_balance(self):
        raise NotImplementedError

class CBXScanner:
    """
    Main orchestration loop for the CBX Strategy.
    """
    def __init__(
        self,
        db_factory,
        data_fetcher: DataFetcher,
        order_executor: OrderExecutor,
        config: dict
    ):
        self.db_factory = db_factory
        self.data_fetcher = data_fetcher
        self.order_executor = order_executor
        self.config = config
        
        self.compression_detector = CompressionDetector()
        self.breakout_detector = BreakoutDetector()
        self.expansion_validator = ExpansionValidator()
        self.context_filter = ContextFilter()
        self.risk_engine = RiskEngine()
        self.entry_engine = EntryEngine()
        self.trade_manager = TradeManager()
        
        self._running = False
        self._active_tasks = set()
        self.scan_interval = int(config.get("BOT_SCAN_INTERVAL_SECONDS", 30))
        self.run_id = UUID(config["RUN_ID"])

    async def start(self):
        self._running = True
        logger.info("Scanner started.")
        while self._running:
            start_time = datetime.utcnow()
            await self.scan_all_symbols()
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            await asyncio.sleep(max(0, self.scan_interval - elapsed))

    async def stop(self):
        self._running = False
        logger.info("Scanner stopping and canceling tasks...")
        for task in self._active_tasks:
            task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        self._active_tasks.clear()
        logger.info("Scanner stopped.")

    async def scan_all_symbols(self):
        symbols = self.config.get("TRADING_SYMBOLS", [])
        for symbol_name in symbols:
            try:
                await self._scan_symbol(symbol_name)
            except Exception as e:
                logger.error(f"Error scanning {symbol_name}: {str(e)}", exc_info=True)

    async def _scan_symbol(self, symbol_name: str):
        async with self.db_factory() as db:
            # 0. Load symbol metadata and configs (Optimized: combined fetch)
            stmt = select(SymbolRegistry).where(SymbolRegistry.symbol == symbol_name)
            res = await db.execute(stmt)
            symbol_reg = res.scalar_one_or_none()
            if not symbol_reg:
                logger.warning(f"Symbol {symbol_name} not found in registry")
                return
            
            symbol_id = symbol_reg.symbol_id
            
            # Load configs
            stmt_conf = select(SymbolStrategyConfig).where(
                SymbolStrategyConfig.symbol_id == symbol_id,
                SymbolStrategyConfig.is_current == True
            )
            stmt_ex = select(SymbolExchangeConfig).where(
                SymbolExchangeConfig.symbol_id == symbol_id
            ).order_by(SymbolExchangeConfig.fetched_at.desc())
            
            res_conf, res_ex = await asyncio.gather(db.execute(stmt_conf), db.execute(stmt_ex))
            
            strat_config = res_conf.scalar_one_or_none()
            ex_config = res_ex.scalars().first()
            
            if not strat_config or not ex_config:
                logger.warning(f"Configs missing for {symbol_name}")
                return

            # 1. Fetch Data
            df_15m = await self.data_fetcher.get_klines(symbol_name, "15m", limit=200)
            df_1h = await self.data_fetcher.get_klines(symbol_name, "1h", limit=2160)
            if df_15m is None or df_1h is None: return

            # 2. Compute Features (placeholder for actual engine calls)
            # df_15m = feature_engine.compute(df_15m, df_1h, strat_config)
            
            current_bar = df_15m.iloc[-1].to_dict()

            # 3. Update Open Trades
            stmt_trades = select(Trade).where(
                Trade.symbol_id == symbol_id,
                Trade.status == "OPEN"
            )
            res_trades = await db.execute(stmt_trades)
            open_trades = res_trades.scalars().all()
            
            # Find active zone for management
            stmt_zone = select(CompressionEvent).where(
                CompressionEvent.symbol_id == symbol_id,
                CompressionEvent.is_active == True
            )
            res_active_zone = await db.execute(stmt_zone)
            active_zone = res_active_zone.scalar_one_or_none()

            for trade in open_trades:
                # Update metrics
                self.trade_manager.update_mfe_mae(trade, current_bar)
                trade.hold_bars = (trade.hold_bars or 0) + 1 # Simple increment
                
                # Check exit conditions
                if active_zone:
                    action = self.trade_manager.update(trade, current_bar, active_zone, strat_config.__dict__)
                    if action.action_type != "HOLD":
                        await self._execute_trade_action(trade, action, symbol_name, symbol_id, db)

            # 4. Detection Pipeline
            # 4.1 Compression
            zone = self.compression_detector.detect(df_15m, self.run_id, symbol_id, strat_config.__dict__)
            if not zone:
                return

            # 4.2 Breakout
            breakout = self.breakout_detector.detect(current_bar, zone, df_15m.iloc[-1], strat_config.__dict__)
            # await self.breakout_detector.save_event(breakout, ...) 
            # (Note: In actual app, we'd save to DB here)
            
            if not breakout.is_valid:
                return

            # 5. Context Filter
            ctx = self.context_filter.check(df_1h, breakout.side, breakout, strat_config.__dict__)
            if not ctx.allowed:
                return

            # 6. Wait for Expansion (Managed Task)
            task = asyncio.create_task(
                self._wait_for_expansion(breakout, zone, symbol_name, symbol_id, strat_config)
            )
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

    async def _wait_for_expansion(self, breakout, zone, symbol_name, symbol_id, config):
        # Polling for next 3 bars
        # For simplicity in this mock, we wait short intervals
        # Real logic: check every 15m or look at current incomplete bars
        bars_collected = []
        lookforward = int(config.expansion_lookforward_bars)
        
        for _ in range(lookforward):
            await asyncio.sleep(5) # Simulation sleep
            # Fetch latest data
            df = await self.data_fetcher.get_klines(symbol_name, "15m", limit=5)
            bars_collected.append(df.iloc[-1].to_dict())
            
            expansion = self.expansion_validator.validate(breakout, bars_collected, zone, config.__dict__)
            if expansion.is_confirmed:
                await self._handle_signal(expansion, breakout, zone, symbol_name, symbol_id, config)
                return
            if not expansion.is_valid:
                return

    async def _handle_signal(self, expansion, breakout, zone, symbol_name, symbol_id, config):
        # Implementation of signal handling
        mode = self.config.get("BOT_DEFAULT_MODE", "manual")
        if mode == "auto":
            await self._execute_entry(expansion, breakout, zone, symbol_name, symbol_id, config)
        else:
            logger.info(f"Signal detected for {symbol_name} ({breakout.side}) - Manual Mode")

    async def _execute_entry(self, expansion, breakout, zone, symbol_name, symbol_id, config):
        async with self.db_factory() as db:
            # Risk Check
            risk_res = await self.risk_engine.check_can_trade(symbol_id, self.run_id, db, config.__dict__)
            if not risk_res.allowed:
                logger.info(f"Entry blocked by risk: {risk_res.block_reason}")
                return

            # Stop Loss
            sl_price = self.risk_engine.calculate_stop_loss(breakout.side, zone, breakout.breakout_bar, config.__dict__)
            
            # Entry Preparation
            model = "FOLLOW_THROUGH" # Default or from config
            entry_order = self.entry_engine.prepare_entry(expansion, breakout, zone, model, config.__dict__, sl_price)
            
            # Execution Check
            df = await self.data_fetcher.get_klines(symbol_name, "15m", limit=2)
            current_bar = df.iloc[-1].to_dict()
            if not self.entry_engine.is_still_valid(entry_order, current_bar, zone, zone.atr_value):
                logger.info("Entry invalidated before execution")
                return

            # Position Sizing
            equity = await self.order_executor.get_account_balance()
            # exchange config needed here, load it or pass it
            # For brevity, let's assume we have it
            # size_res = self.risk_engine.calculate_position_size(...)
            
            # place order
            # order_res = await self.order_executor.place_market_order(...)
            
            # update session
            await self.risk_engine.update_session_on_open(symbol_id, self.run_id, db)
            
            # Create Trade record
            new_trade = Trade(
                expansion_id=expansion.expansion_id if hasattr(expansion, 'expansion_id') else uuid4(), # Fallback for mock
                run_id=self.run_id,
                symbol_id=symbol_id,
                side=breakout.side,
                entry_model=model,
                entry_time=datetime.utcnow(),
                entry_price=entry_order.price,
                stop_loss_price=entry_order.stop_loss,
                tp1_price=entry_order.tp1_price,
                initial_risk_r_price=entry_order.price - entry_order.stop_loss if breakout.side == "LONG" else entry_order.stop_loss - entry_order.price,
                position_size=Decimal("0.1"), # Placeholder for result of sizing
                position_size_usd=Decimal("100"),
                risk_amount_usd=Decimal("10"),
                status="OPEN"
            )
            db.add(new_trade)
            try:
                await db.commit()
                logger.info(f"New trade opened: {symbol_name} {breakout.side} at {entry_order.price}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to commit new trade for {symbol_name}: {str(e)}")

    async def _execute_trade_action(self, trade, action, symbol_name, symbol_id, db):
        logger.info(f"Executing {action.action_type} for {symbol_name} (Reason: {action.reason})")
        
        if action.action_type == "CLOSE_FULL":
            trade.status = "CLOSED"
            trade.exit_time = datetime.utcnow()
            trade.avg_exit_price = Decimal(str(action.price))
            trade.exit_model = action.reason
            # Session update
            await self.risk_engine.update_session_on_close(symbol_id, self.run_id, db, trade.total_pnl_r or Decimal("0"), action.reason)
            
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit trade action for {symbol_name}: {str(e)}")
