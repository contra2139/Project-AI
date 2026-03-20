from typing import Optional, List
from decimal import Decimal
from dataclasses import dataclass
from app.models.trade import Trade
from app.models.events import CompressionEvent

@dataclass
class TradeAction:
    action_type: str  # "HOLD", "CLOSE_PARTIAL", "CLOSE_FULL"
    exit_type: Optional[str] = None # "STOP_LOSS", "PARTIAL_1R", "TRAILING", "TIME_STOP", "STRUCTURE_FAIL"
    close_price: Optional[Decimal] = None
    size_to_close: Optional[Decimal] = None
    reason: str = ""

class TradeManager:
    """
    Manages the lifecycle of an OPEN trade.
    Determines exit actions based on price action and strategy rules.
    """

    def update(
        self,
        trade: Trade,
        current_bar: dict,
        zone: CompressionEvent,
        config: dict
    ) -> TradeAction:
        """
        Evaluates current market state against trade rules and returns action.
        Priority: SL > Structure Fail > Time Stop > Partial 1R > Trailing
        """
        curr_low = Decimal(str(current_bar['low']))
        curr_high = Decimal(str(current_bar['high']))
        curr_close = Decimal(str(current_bar['close']))
        
        # 1. STOP_LOSS (Priority 1)
        if trade.side == "LONG" and curr_low <= trade.stop_loss_price:
            return TradeAction("CLOSE_FULL", "STOP_LOSS", trade.stop_loss_price, reason="Stop loss hit")
        if trade.side == "SHORT" and curr_high >= trade.stop_loss_price:
            return TradeAction("CLOSE_FULL", "STOP_LOSS", trade.stop_loss_price, reason="Stop loss hit")

        # 2. STRUCTURE_FAIL
        # Long: Close below zone low. Short: Close above zone high.
        if trade.side == "LONG" and curr_close < Decimal(str(zone.low)):
            return TradeAction("CLOSE_FULL", "STRUCTURE_FAIL", curr_close, reason="Zone floor breached")
        if trade.side == "SHORT" and curr_close > Decimal(str(zone.high)):
            return TradeAction("CLOSE_FULL", "STRUCTURE_FAIL", curr_close, reason="Zone ceiling breached")

        # 3. TIME_STOP (Bug 1 Fix)
        # Check hold_bars >= time_stop_bars AND pnl_r < 1.0
        time_stop_bars = int(config.get("time_stop_bars", 8))
        partial_exit_r = Decimal(str(config.get("partial_exit_r_level", "1.0")))
        
        if trade.hold_bars >= time_stop_bars:
            pnl_r = self._calculate_current_pnl_r(trade, curr_close)
            if pnl_r < partial_exit_r:
                return TradeAction("CLOSE_FULL", "TIME_STOP", curr_close, reason=f"Time stop: {trade.hold_bars} bars without {partial_exit_r}R")

        # 3.1 HARD LIMIT (Bug 2 Fix)
        # Safety net: Force close if trade exceeds 50 bars
        if trade.hold_bars > 50:
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(f"HARD LIMIT BREACH: Trade {trade.trade_id} held for {trade.hold_bars} bars. Force closing.")
            return TradeAction("CLOSE_FULL", "FORCE_CLOSE_HARD", curr_close, reason="Hard limit (50 bars) exceeded")

        # 4. PARTIAL_1R
        if not trade.partial_exit_done:
            if trade.side == "LONG" and curr_high >= trade.tp1_price:
                partial_pct = Decimal(str(config.get("partial_exit_pct", "0.50")))
                return TradeAction("CLOSE_PARTIAL", "PARTIAL_1R", trade.tp1_price, 
                                   size_to_close=trade.position_size * partial_pct, 
                                   reason="Target 1R reached")
            if trade.side == "SHORT" and curr_low <= trade.tp1_price:
                partial_pct = Decimal(str(config.get("partial_exit_pct", "0.50")))
                return TradeAction("CLOSE_PARTIAL", "PARTIAL_1R", trade.tp1_price,
                                   size_to_close=trade.position_size * partial_pct,
                                   reason="Target 1R reached")

        # 5. TRAILING (Only after partial)
        if trade.partial_exit_done:
            # Trailing stop logic (e.g. 2-bar low/high vs 1.5 ATR floor)
            # Update trailing stop price if not already updated this bar by the engine
            if trade.trailing_stop_price:
                if trade.side == "LONG" and curr_low <= trade.trailing_stop_price:
                    return TradeAction("CLOSE_FULL", "TRAILING", trade.trailing_stop_price, reason="Trailing stop hit")
                if trade.side == "SHORT" and curr_high >= trade.trailing_stop_price:
                    return TradeAction("CLOSE_FULL", "TRAILING", trade.trailing_stop_price, reason="Trailing stop hit")

        return TradeAction("HOLD", reason="No exit conditions met")

    def update_mfe_mae(self, trade: Trade, current_bar: dict):
        """
        Updates Maximum Favorable Excursion and Maximum Adverse Excursion in R.
        """
        curr_low = Decimal(str(current_bar['low']))
        curr_high = Decimal(str(current_bar['high']))
        
        if trade.side == "LONG":
            favorable = curr_high
            adverse = curr_low
        else:
            favorable = curr_low
            adverse = curr_high
            
        risk_dist = trade.initial_risk_r_price
        if risk_dist == 0: return

        mfe_r = (favorable - trade.entry_price) / risk_dist if trade.side == "LONG" else (trade.entry_price - favorable) / risk_dist
        mae_r = (trade.entry_price - adverse) / risk_dist if trade.side == "LONG" else (adverse - trade.entry_price) / risk_dist
        
        trade.MFE_r = max(trade.MFE_r or Decimal("0"), mfe_r)
        trade.MAE_r = max(trade.MAE_r or Decimal("0"), mae_r)
        
    def get_trailing_stop(self, trade: Trade, recent_bars: List[dict], zone: CompressionEvent, config: dict) -> Optional[Decimal]:
        """
        Calculates Strategy V4 Trailing Stop:
        Tighter of (2-bar low/high) or (Entry Price +/- 1.5 * Entry ATR).
        Includes Ratchet logic: Never moves backwards.
        """
        if len(recent_bars) < 2:
            return trade.trailing_stop_price
            
        multiplier = Decimal(str(config.get("trailing_atr_multiplier", "1.5")))

        # 1. Calculate 2-bar low/high
        if trade.side == "LONG":
            two_bar_low = min(Decimal(str(recent_bars[-1]['low'])), Decimal(str(recent_bars[-2]['low'])))
            # 2. Calculate ATR from entry floor
            entry_atr = Decimal(str(getattr(trade, 'entry_zone', zone).atr_value))
            atr_floor = trade.entry_price + (multiplier * entry_atr)
            
            # 3. Whichever is tighter (Higher for LONG)
            calculated = max(two_bar_low, atr_floor)
            
            # 4. Ratchet Logic
            if trade.trailing_stop_price is None:
                return calculated
            return max(trade.trailing_stop_price, calculated)
            
        else: # SHORT
            two_bar_high = max(Decimal(str(recent_bars[-1]['high'])), Decimal(str(recent_bars[-2]['high'])))
            # 2. Calculate ATR from entry floor
            entry_atr = Decimal(str(getattr(trade, 'entry_zone', zone).atr_value))
            atr_floor = trade.entry_price - (multiplier * entry_atr)
            
            # 3. Whichever is tighter (Lower for SHORT)
            calculated = min(two_bar_high, atr_floor)
            
            # 4. Ratchet Logic
            if trade.trailing_stop_price is None:
                return calculated
            return min(trade.trailing_stop_price, calculated)

    def _calculate_current_pnl_r(self, trade: Trade, current_price: Decimal) -> Decimal:
        if trade.initial_risk_r_price == 0: return Decimal("0")
        if trade.side == "LONG":
            return (current_price - trade.entry_price) / trade.initial_risk_r_price
        else:
            return (trade.entry_price - current_price) / trade.initial_risk_r_price
