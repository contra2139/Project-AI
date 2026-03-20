from typing import List, Optional, Literal, Tuple
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from app.models.events import CompressionEvent, BreakoutEvent
from sqlalchemy.orm import Session

@dataclass
class BreakoutResult:
    is_valid: bool = False
    side: Optional[Literal["LONG", "SHORT"]] = None
    invalid_reasons: List[str] = field(default_factory=list)
    condition_checks: List[Tuple[str, Decimal, Decimal, bool]] = field(default_factory=list)
    breakout_price_level: Decimal = Decimal("0")
    breakout_distance_atr: Decimal = Decimal("0")
    bar_size_atr: Decimal = Decimal("0")
    body_to_range: Decimal = Decimal("0")
    close_position_in_candle: Decimal = Decimal("0")
    vol_ratio: Decimal = Decimal("0")
    vol_percentile: Decimal = Decimal("0")
    is_wick_dominant: bool = False
    breakout_bar: dict = field(default_factory=dict)

class BreakoutDetector:
    """
    Detects breakout from a compression zone with high-precision filters.
    """
    
    def detect(self, current_bar: pd.Series, zone: CompressionEvent, feature_row: pd.Series, config: dict) -> BreakoutResult:
        res = BreakoutResult()
        res.breakout_bar = current_bar.to_dict()
        
        # 1. Banned Filters (Early Exit)
        atr = Decimal(str(feature_row.get('atr', 1)))
        candle_high = Decimal(str(current_bar['high']))
        candle_low = Decimal(str(current_bar['low']))
        candle_open = Decimal(str(current_bar['open']))
        candle_close = Decimal(str(current_bar['close']))
        candle_range = candle_high - candle_low
        
        # Banned: False Break Limit
        if zone.false_break_count >= config.get("false_break_limit", 2):
            res.invalid_reasons.append("BANNED_FALSE_BREAK_LIMIT")
            return res
            
        # Banned: Doji
        if candle_range == 0:
            res.invalid_reasons.append("INVALID_DOJI_ZERO_RANGE")
            return res
            
        # Banned: Candle Size (> max_atr)
        bar_size_atr = candle_range / atr
        res.bar_size_atr = bar_size_atr
        max_bar_size = Decimal(str(config.get("breakout_bar_size_max_atr", "2.5")))
        if bar_size_atr > max_bar_size:
            res.invalid_reasons.append("BAR_TOO_LARGE")
            res.condition_checks.append(("BAR_SIZE_ATR", bar_size_atr, max_bar_size, False))
            return res

        # 2. Side Detection
        zone_high = Decimal(str(zone.high))
        zone_low = Decimal(str(zone.low))
        
        if candle_close > zone_high:
            res.side = "LONG"
            res.breakout_price_level = zone_high
        elif candle_close < zone_low:
            res.side = "SHORT"
            res.breakout_price_level = zone_low
        else:
            res.invalid_reasons.append("NO_BREAKOUT_SIDE")
            return res

        # 3. 7 Validation Conditions
        # C1: Side Detection (Already checked above)
        res.condition_checks.append(("SIDE_DETECTION", Decimal("1"), Decimal("1"), True))
        
        # C2: Breakout Distance
        breakout_dist = abs(candle_close - res.breakout_price_level)
        breakout_dist_atr = breakout_dist / atr
        res.breakout_distance_atr = breakout_dist_atr
        min_dist_atr = Decimal(str(config.get("breakout_distance_min_atr", "0.20")))
        passed_dist = breakout_dist_atr >= min_dist_atr
        res.condition_checks.append(("BREAKOUT_DISTANCE", breakout_dist_atr, min_dist_atr, bool(passed_dist)))
        if not passed_dist:
            res.invalid_reasons.append("DISTANCE_TOO_SMALL")
            
        # C3: Body Ratio
        body_size = abs(candle_close - candle_open)
        body_to_range = body_size / candle_range
        res.body_to_range = body_to_range
        min_body_ratio = Decimal(str(config.get("breakout_body_ratio_min", "0.60")))
        passed_body = body_to_range >= min_body_ratio
        res.condition_checks.append(("BODY_RATIO", body_to_range, min_body_ratio, bool(passed_body)))
        if not passed_body:
            res.invalid_reasons.append("BODY_RATIO_TOO_LOW")
            
        # C4: Close Position
        if res.side == "LONG":
            close_pos = (candle_close - candle_low) / candle_range
            min_close_pos = Decimal(str(config.get("breakout_close_position_long", "0.75")))
        else:
            close_pos = (candle_high - candle_close) / candle_range
            min_close_pos = Decimal(str(config.get("breakout_close_position_short", "0.35")))
            
        res.close_position_in_candle = close_pos
        passed_pos = close_pos >= min_close_pos
        res.condition_checks.append(("CLOSE_POSITION", close_pos, min_close_pos, bool(passed_pos)))
        if not passed_pos:
            res.invalid_reasons.append("CLOSE_POSITION")
            
        # C5: Volume Quality
        vol_ratio = Decimal(str(feature_row.get('vol_ratio', 1)))
        vol_pct = Decimal(str(feature_row.get('vol_ratio_pct', 0)))
        res.vol_ratio = vol_ratio
        res.vol_percentile = vol_pct
        
        min_vol_ratio = Decimal(str(config.get("breakout_volume_ratio_min", "1.30")))
        min_vol_pct = Decimal(str(config.get("breakout_volume_percentile_min", "70.0")))
        
        passed_vol = (vol_ratio >= min_vol_ratio) or (vol_pct >= min_vol_pct)
        res.condition_checks.append(("VOLUME_QUALITY", vol_ratio, min_vol_ratio, bool(passed_vol)))
        if not passed_vol:
            res.invalid_reasons.append("VOL_TOO_LOW")
            
        # C6: Size Limit
        passed_size = bar_size_atr <= max_bar_size
        res.condition_checks.append(("BAR_SIZE_ATR", bar_size_atr, max_bar_size, bool(passed_size)))
        if not passed_size:
            # Although checked in Banned GĐ1, we keep this for collect-all logic if we ever remove return from GĐ1
            res.invalid_reasons.append("BAR_TOO_LARGE")

        # C7: Wick Dominance
        if res.side == "LONG":
            opposite_wick = candle_open - candle_low
        else:
            opposite_wick = candle_high - candle_open
            
        wick_ratio = Decimal(str(config.get("wick_dominance_ratio", "1.5")))
        res.is_wick_dominant = opposite_wick > (body_size * wick_ratio)
        passed_wick = not res.is_wick_dominant
        res.condition_checks.append(("WICK_DOMINANCE", opposite_wick, body_size * wick_ratio, bool(passed_wick)))
        if not passed_wick:
            res.invalid_reasons.append("WICK_DOMINANT")

        # Final Result
        res.is_valid = len(res.invalid_reasons) == 0
        return res

    def save_event(self, result: BreakoutResult, compression_id: int, run_id: int, db: Session) -> BreakoutEvent:
        if not result.is_valid:
            return None
            
            ts = result.breakout_bar['timestamp']
            if hasattr(ts, 'timestamp'):
                dt = datetime.fromtimestamp(ts.timestamp())
            else:
                dt = datetime.fromtimestamp(ts / 1000)
            
            event = BreakoutEvent(
                compression_id=compression_id,
                run_id=run_id,
                timestamp=dt,
            side=result.side,
            breakout_price=float(result.breakout_bar['close']),
            distance_atr=float(result.breakout_distance_atr),
            volume_ratio=float(result.vol_ratio),
            body_ratio=float(result.body_to_range)
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def save_filter_logs(self, result: BreakoutResult, symbol: str, run_id: int, db: Session):
        # Implementation of FILTER_LOG saving loop
        # For now, we simulate writing to log output since model for FILTER_LOG 
        # might need to be created/verified.
        pass
