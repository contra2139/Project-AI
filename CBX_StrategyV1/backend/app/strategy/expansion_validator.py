from typing import List, Optional, Literal
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime
from app.models.events import CompressionEvent, BreakoutEvent, ExpansionEvent
from app.strategy.breakout_detector import BreakoutResult
from sqlalchemy.orm import Session

@dataclass
class ExpansionResult:
    is_confirmed: bool = False
    rejection_reasons: List[str] = field(default_factory=list)
    confirmation_bar_index: Optional[int] = None  # 1, 2, or 3
    confirmed_by: Optional[str] = None  # "CONDITION_A" or "CONDITION_B"
    confirmation_time: Optional[datetime] = None
    max_extension_price: Decimal = Decimal("0")
    max_extension_atr: Decimal = Decimal("0")
    reentry_occurred: bool = False
    reentry_depth_pct: Decimal = Decimal("0")
    body_loss_pct: Decimal = Decimal("0")  # Max body loss encountered
    higher_high_formed: Optional[bool] = None
    lower_low_formed: Optional[bool] = None

class ExpansionValidator:
    """
    Validates expansion after a breakout.
    Checks for flow-through (Condition A) or holding above/below (Condition B) within 3 bars.
    """
    
    def validate(self, breakout: BreakoutResult, next_bars: List[dict], zone: CompressionEvent, config: dict) -> ExpansionResult:
        res = ExpansionResult()
        if not breakout.is_valid:
            res.rejection_reasons.append("BREAKOUT_INVALID")
            return res
            
        breakout_bar_high = Decimal(str(breakout.breakout_bar['high']))
        breakout_bar_low = Decimal(str(breakout.breakout_bar['low']))
        breakout_bar_close = Decimal(str(breakout.breakout_bar['close']))
        breakout_bar_open = Decimal(str(breakout.breakout_bar['open']))
        breakout_body_size = abs(breakout_bar_close - breakout_bar_open)
        
        breakout_price_level = breakout.breakout_price_level
        atr = breakout.bar_size_atr * 0 # This is wrong, I need the actual ATR from feature_row or zone.
        # Wait, breakout.bar_size_atr is candle_range / atr. 
        # So ATR = candle_range / breakout.bar_size_atr.
        candle_range = breakout_bar_high - breakout_bar_low
        atr = candle_range / breakout.bar_size_atr if breakout.bar_size_atr > 0 else Decimal("1")
        
        max_body_loss_pct = Decimal("0")
        max_ext_price = breakout_bar_close
        
        zone_high = Decimal(str(zone.high))
        zone_low = Decimal(str(zone.low))
        zone_width = zone_high - zone_low
        
        max_body_loss_limit = Decimal(str(config.get("expansion_body_loss_max_pct", 50)))
        
        for i, bar in enumerate(next_bars):
            idx = i + 1
            curr_high = Decimal(str(bar['high']))
            curr_low = Decimal(str(bar['low']))
            curr_close = Decimal(str(bar['close']))
            curr_open = Decimal(str(bar['open']))
            
            # --- Extension Tracking ---
            if breakout.side == "LONG":
                max_ext_price = max(max_ext_price, curr_high)
                # Body Loss (Long): (Close - Low) / Body
                if breakout_body_size > 0:
                    body_loss_pct = (breakout_bar_close - curr_low) / breakout_body_size * 100
                else:
                    body_loss_pct = Decimal("0")
            else:
                max_ext_price = min(max_ext_price, curr_low)
                # Body Loss (Short): (High - Close) / Body
                if breakout_body_size > 0:
                    body_loss_pct = (curr_high - breakout_bar_close) / breakout_body_size * 100
                else:
                    body_loss_pct = Decimal("0")
            
            max_body_loss_pct = max(max_body_loss_pct, body_loss_pct)
            
            # --- Reentry Tracking ---
            if breakout.side == "LONG":
                if curr_low < zone_high:
                    res.reentry_occurred = True
                    depth = (zone_high - curr_low) / zone_width * 100 if zone_width > 0 else Decimal("0")
                    res.reentry_depth_pct = max(res.reentry_depth_pct, depth)
            else:
                if curr_high > zone_low:
                    res.reentry_occurred = True
                    depth = (curr_high - zone_low) / zone_width * 100 if zone_width > 0 else Decimal("0")
                    res.reentry_depth_pct = max(res.reentry_depth_pct, depth)

            # --- 1. Check Rejected Conditions ---
            # REENTRY_DEEP
            if breakout.side == "LONG" and curr_close < zone_high:
                res.rejection_reasons.append("REENTRY_DEEP")
                break
            if breakout.side == "SHORT" and curr_close > zone_low:
                res.rejection_reasons.append("REENTRY_DEEP")
                break
                
            # BODY_LOSS_EXCEEDED
            if body_loss_pct >= max_body_loss_limit:
                res.rejection_reasons.append("BODY_LOSS_EXCEEDED")
                break
                
            # --- 2. Check Confirmation Conditions ---
            # Condition A — Flow-through (Higher High / Lower Low)
            if breakout.side == "LONG":
                if curr_high > breakout_bar_high and curr_close > zone_high:
                    res.is_confirmed = True
                    res.confirmed_by = "CONDITION_A"
                    res.confirmation_bar_index = idx
                    res.higher_high_formed = True
                    ts = bar['timestamp']
                    if hasattr(ts, 'timestamp'):
                        res.confirmation_time = datetime.fromtimestamp(ts.timestamp())
                    else:
                        res.confirmation_time = datetime.fromtimestamp(ts / 1000)
                    break
            else:
                if curr_low < breakout_bar_low and curr_close < zone_low:
                    res.is_confirmed = True
                    res.confirmed_by = "CONDITION_A"
                    res.confirmation_bar_index = idx
                    res.lower_low_formed = True
                    ts = bar['timestamp']
                    if hasattr(ts, 'timestamp'):
                        res.confirmation_time = datetime.fromtimestamp(ts.timestamp())
                    else:
                        res.confirmation_time = datetime.fromtimestamp(ts / 1000)
                    break
            
            # Condition B — Hold Above
            if idx >= 2:
                 res.is_confirmed = True
                 res.confirmed_by = "CONDITION_B"
                 res.confirmation_bar_index = idx
                 ts = bar['timestamp']
                 if hasattr(ts, 'timestamp'):
                     res.confirmation_time = datetime.fromtimestamp(ts.timestamp())
                 else:
                     res.confirmation_time = datetime.fromtimestamp(ts / 1000)
                 break

        # Final Cleanup & Results
        res.body_loss_pct = max_body_loss_pct
        res.max_extension_price = max_ext_price
        res.max_extension_atr = abs(max_ext_price - breakout_price_level) / atr if atr > 0 else Decimal("0")
        
        if not res.is_confirmed and not res.rejection_reasons:
            if len(next_bars) >= config.get("expansion_lookforward_bars", 3):
                res.rejection_reasons.append("NO_FOLLOWTHROUGH")
                
        return res

    def save_event(self, result: ExpansionResult, breakout_id: int, run_id: int, db: Session) -> Optional[ExpansionEvent]:
        if not result.is_confirmed:
            return None
            
        event = ExpansionEvent(
            breakout_id=breakout_id,
            run_id=run_id,
            is_confirmed=True,
            confirmation_time=result.confirmation_time,
            confirmed_by=result.confirmed_by,
            max_extension_atr=Decimal(str(result.max_extension_atr)),
            body_loss_pct=Decimal(str(result.body_loss_pct)),
            reentry_occurred=result.reentry_occurred,
            reentry_depth_pct=Decimal(str(result.reentry_depth_pct))
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def save_filter_logs(self, result: ExpansionResult, breakout_id: int, run_id: int, db: Session):
        # Implementation for structured logs
        pass
