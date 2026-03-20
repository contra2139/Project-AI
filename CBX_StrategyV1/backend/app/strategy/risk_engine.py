from typing import Optional, Literal, Tuple
from decimal import Decimal
import math
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.session import SessionState, EquitySnapshot
from app.models.events import CompressionEvent

@dataclass
class RiskCheckResult:
    allowed: bool
    block_reason: Optional[str] = None
    current_daily_pnl_r: Decimal = Decimal("0")
    consecutive_failures: int = 0
    open_position_count: int = 0
    portfolio_position_count: int = 0

@dataclass
class PositionSizeResult:
    qty: Decimal
    valid: bool
    invalid_reason: Optional[str] = None
    risk_amount_usd: Decimal = Decimal("0")
    notional_usd: Decimal = Decimal("0")
    price_distance: Decimal = Decimal("0")
    raw_qty: Decimal = Decimal("0")

class RiskEngine:
    """
    Risk Management Engine for CBX Strategy.
    Handles trade permissions, position sizing, and stop-loss calculations.
    """

    async def check_can_trade(
        self, 
        symbol_id: UUID, 
        run_id: UUID,
        db: AsyncSession,
        config: dict
    ) -> RiskCheckResult:
        """
        Validates if a new trade can be opened based on risk guardrails.
        """
        # 1. Load SessionState for the symbol
        stmt = select(SessionState).where(
            SessionState.symbol_id == symbol_id,
            SessionState.run_id == run_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            # If no session, wait for scanner to initialize it or return default allowed=True
            # For now, let's assume allowed if not exists (or scanner creates it)
            return RiskCheckResult(allowed=True)

        res = RiskCheckResult(
            allowed=True,
            current_daily_pnl_r=session.current_daily_pnl_r,
            consecutive_failures=session.consecutive_failures,
            open_position_count=session.open_position_count
        )

        # 2. Check if trading is halted
        if session.trading_halted:
            res.allowed = False
            res.block_reason = "TRADING_HALTED"
            return res

        # 3. Daily Stop R
        daily_stop_r = Decimal(str(config.get("risk_daily_stop_r", "-2.0")))
        if session.current_daily_pnl_r <= daily_stop_r:
            session.trading_halted = True
            session.halt_reason = "DAILY_STOP"
            session.halt_at = datetime.utcnow()
            await db.commit()
            res.allowed = False
            res.block_reason = "DAILY_STOP"
            return res

        # 4. Consecutive Failures
        max_consecutive = int(config.get("risk_consecutive_fail_stop", 3))
        if session.consecutive_failures >= max_consecutive:
            session.trading_halted = True
            session.halt_reason = "CONSECUTIVE_FAIL"
            session.halt_at = datetime.utcnow()
            await db.commit()
            res.allowed = False
            res.block_reason = "CONSECUTIVE_FAIL"
            return res

        # 5. Max Position per Symbol
        max_pos_symbol = int(config.get("max_position_per_symbol", 1))
        if session.open_position_count >= max_pos_symbol:
            res.allowed = False
            res.block_reason = "MAX_POSITION_SYMBOL"
            return res

        # 6. Max Position Portfolio
        max_pos_portfolio = int(config.get("risk_max_positions_portfolio", 2))
        portfolio_stmt = select(func.sum(SessionState.open_position_count)).where(
            SessionState.run_id == run_id
        )
        port_res = await db.execute(portfolio_stmt)
        total_open = port_res.scalar() or 0
        res.portfolio_position_count = total_open
        
        if total_open >= max_pos_portfolio:
            res.allowed = False
            res.block_reason = "MAX_POSITION_PORTFOLIO"
            return res

        return res

    def calculate_position_size(
        self,
        entry_price: Decimal,
        stop_price: Decimal,
        equity_usd: Decimal,
        config: dict,
        exchange_config: dict # contains lot_size_step, min_qty, min_notional
    ) -> PositionSizeResult:
        """
        Calculates position size using fixed risk % of equity.
        """
        risk_pct = Decimal(str(config.get("risk_per_trade_pct", "0.0025")))
        risk_amount = equity_usd * risk_pct
        price_dist = abs(entry_price - stop_price)
        
        if price_dist == 0:
            return PositionSizeResult(qty=Decimal("0"), valid=False, invalid_reason="ZERO_STOP_DISTANCE")

        raw_qty = risk_amount / price_dist
        
        # Round DOWN according to lot_size_step
        lot_step = Decimal(str(exchange_config.get("lot_size_step", "0.001")))
        # qty = floor(raw_qty / lot_step) * lot_step
        rounded_qty = (raw_qty / lot_step).to_integral_value(rounding="ROUND_FLOOR") * lot_step
        
        res = PositionSizeResult(
            qty=rounded_qty,
            valid=True,
            risk_amount_usd=risk_amount,
            notional_usd=rounded_qty * entry_price,
            price_distance=price_dist,
            raw_qty=raw_qty
        )
        
        # Min Qty Check
        min_qty = Decimal(str(exchange_config.get("min_qty", "0.001")))
        if rounded_qty < min_qty:
            res.valid = False
            res.invalid_reason = "MIN_QTY_NOT_MET"
            return res
            
        # Min Notional Check
        min_notional = Decimal(str(exchange_config.get("min_notional", "5.0")))
        if res.notional_usd < min_notional:
            res.valid = False
            res.invalid_reason = "MIN_NOTIONAL_NOT_MET"
            return res
            
        return res

    def calculate_stop_loss(
        self,
        side: Literal["LONG", "SHORT"],
        zone: CompressionEvent,
        breakout_bar: dict,
        config: dict
    ) -> Decimal:
        """
        Calculates ATR-based Stop Loss.
        LONG: min(ZoneHigh - Buffer, BreakoutBarLow)
        SHORT: max(ZoneLow + Buffer, BreakoutBarHigh)
        """
        atr_val = Decimal(str(zone.atr_value))
        buffer_val = Decimal(str(config.get("stop_loss_atr_buffer", "0.25")))
        atr_buffer = atr_val * buffer_val
        
        zone_high = Decimal(str(zone.high))
        zone_low = Decimal(str(zone.low))
        
        if side == "LONG":
            level_1 = zone_high - atr_buffer
            level_2 = Decimal(str(breakout_bar['low']))
            return min(level_1, level_2)
        else:
            level_1 = zone_low + atr_buffer
            level_2 = Decimal(str(breakout_bar['high']))
            return max(level_1, level_2)

    async def update_session_on_open(self, symbol_id: UUID, run_id: UUID, db: AsyncSession):
        stmt = select(SessionState).where(
            SessionState.symbol_id == symbol_id,
            SessionState.run_id == run_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one()
        session.open_position_count += 1
        await db.commit()

    async def update_session_on_close(
        self, 
        symbol_id: UUID, 
        run_id: UUID, 
        pnl_r: Decimal, 
        trade_result: str, 
        db: AsyncSession
    ):
        stmt = select(SessionState).where(
            SessionState.symbol_id == symbol_id,
            SessionState.run_id == run_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one()
        
        session.open_position_count -= 1
        session.current_daily_pnl_r += pnl_r
        
        if trade_result == "FAILED_BREAKOUT":
            session.consecutive_failures += 1
        else:
            # Reset on any result that is not a failed breakout (e.g. TP1, Manual Close)
            session.consecutive_failures = 0
            
        await db.commit()
