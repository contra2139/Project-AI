from typing import Optional, Literal
from decimal import Decimal
from dataclasses import dataclass
from app.strategy.breakout_detector import BreakoutResult
from app.strategy.expansion_validator import ExpansionResult
from app.models.events import CompressionEvent

@dataclass
class EntryOrder:
    is_valid: bool
    invalid_reason: Optional[str] = None
    symbol: str = ""
    side: str = "" # LONG or SHORT
    entry_model: str = "FOLLOW_THROUGH" # or RETEST
    entry_price_estimate: Decimal = Decimal("0")
    stop_loss_price: Decimal = Decimal("0")
    tp1_price: Decimal = Decimal("0")
    initial_r_distance: Decimal = Decimal("0")
    zone_ref: Optional[CompressionEvent] = None
    breakout_bar: Optional[dict] = None
    bars_passed: int = 0

class EntryEngine:
    """
    Prepares entry orders based on Breakout and Expansion results.
    Support Follow-Through (FT) and Retest (RT) models.
    """

    def prepare_entry(
        self,
        expansion: ExpansionResult,
        breakout: BreakoutResult,
        zone: CompressionEvent,
        entry_model: Literal["FOLLOW_THROUGH", "RETEST"],
        config: dict,
        stop_loss_price: Decimal
    ) -> EntryOrder:
        """
        Creates an EntryOrder template.
        """
        if not expansion.is_confirmed:
            return EntryOrder(is_valid=False, invalid_reason="EXPANSION_NOT_CONFIRMED")

        # Estimate entry price
        # For FT: use breakout bar close (approximation of next open)
        # For RT: use breakout edge (zone.high for LONG, zone.low for SHORT)
        
        entry_price = Decimal("0")
        if entry_model == "FOLLOW_THROUGH":
            entry_price = Decimal(str(breakout.breakout_bar['close']))
        else: # RETEST
            if breakout.side == "LONG":
                entry_price = Decimal(str(zone.high))
            else:
                entry_price = Decimal(str(zone.low))
        
        initial_r = abs(entry_price - stop_loss_price)
        tp1 = entry_price + initial_r if breakout.side == "LONG" else entry_price - initial_r

        return EntryOrder(
            is_valid=True,
            symbol=getattr(zone, 'symbol', ''),
            side=breakout.side if breakout.side else "LONG",
            entry_model=entry_model,
            entry_price_estimate=entry_price,
            stop_loss_price=stop_loss_price,
            tp1_price=tp1,
            initial_r_distance=initial_r,
            zone_ref=zone,
            breakout_bar=breakout.breakout_bar
        )

    def is_still_valid(
        self,
        entry_order: EntryOrder,
        current_bar: dict,
        zone: CompressionEvent,
        atr_value: Decimal,
        config: dict
    ) -> bool:
        """
        Final safety check before execution.
        Invalidates if price went too far (configurable, default 1.5 ATR) or closed back in zone.
        """
        curr_close = Decimal(str(current_bar['close']))
        entry_estimate = entry_order.entry_price_estimate
        
        # Max distance check: configurable (default 1.5 ATR)
        max_dist_multiplier = Decimal(str(config.get("entry_max_distance_atr", "1.5")))
        max_dist = atr_value * max_dist_multiplier
        actual_dist = abs(curr_close - entry_estimate)
        
        if actual_dist > max_dist:
            return False
            
        # Zone Reentry check
        if entry_order.side == "LONG":
            # If price closed below zone low, it's a failed breakout
            if curr_close < Decimal(str(zone.low)):
                return False
        else: # SHORT
            if curr_close > Decimal(str(zone.high)):
                return False
                
        return True

    def update_order_status(
        self,
        entry_order: EntryOrder,
        current_bar: dict,
        zone: CompressionEvent,
        config: dict
    ):
        """
        Updates bars_passed and checks for RETEST timeout.
        """
        if not entry_order.is_valid:
            return

        entry_order.bars_passed += 1
        
        if entry_order.entry_model == "RETEST":
            # Check if price reached retest zone in this bar
            atr_val = Decimal(str(zone.atr_value))
            retest_buffer_multiplier = Decimal(str(config.get("entry_retest_buffer_atr", "0.05")))
            buffer = atr_val * retest_buffer_multiplier
            
            high = Decimal(str(current_bar['high']))
            low = Decimal(str(current_bar['low']))
            
            retested = False
            if entry_order.side == "LONG":
                # Retest zone: [edge - buffer, edge + buffer]
                # We check if bar's low touched or went below edge + buffer
                edge = Decimal(str(zone.high))
                if low <= (edge + buffer):
                    retested = True
            else: # SHORT
                edge = Decimal(str(zone.low))
                if high >= (edge - buffer):
                    retested = True
            
            # If retested, we can mark it as "ready to fill" or similar.
            # But the logic here is mostly about TIMEOUT if it HASN'T retested.
            
            max_bars = int(config.get("retest_max_bars", 3))
            if entry_order.bars_passed > max_bars and not retested:
                entry_order.is_valid = False
                entry_order.invalid_reason = "RETEST_TIMEOUT"
