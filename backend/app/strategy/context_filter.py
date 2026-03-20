from typing import List, Optional, Literal
from decimal import Decimal
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from app.strategy.breakout_detector import BreakoutResult
from sqlalchemy.orm import Session

REASON_EMA_LONG_BLOCKED   = "EMA50_LONG_BLOCKED"
REASON_EMA_SHORT_BLOCKED  = "EMA50_SHORT_BLOCKED"  
REASON_SHOCK_BLOCKED      = "VOLATILITY_SHOCK_BLOCKED"
REASON_LOW_VOL_BLOCKED    = "VOLATILITY_LOW_VOL_BLOCKED"

@dataclass
class ContextFilterResult:
    allowed: bool = True
    block_reason: Optional[str] = None
    filter_type: Optional[str] = None  # "EMA50_DIRECTION" or "VOLATILITY_STATE"
    attempted_side: str = ""
    ema50_1h: Decimal = Decimal("0")
    close_1h: Decimal = Decimal("0")
    ema50_slope: Decimal = Decimal("0")
    vol_state: str = "NORMAL"
    vol_percentile_90d: Decimal = Decimal("0")
    realized_vol_1h: Decimal = Decimal("0")
    close_vs_ema50_pct: Decimal = Decimal("0")

class ContextFilter:
    """
    Context Filter to guard against trading against high-TF trend 
    or in extreme volatility regimes.
    """
    
    def check(self, df_1h: pd.DataFrame, attempted_side: Literal["LONG", "SHORT"], breakout_res: BreakoutResult, config: dict) -> ContextFilterResult:
        res = ContextFilterResult(attempted_side=attempted_side)
        
        if df_1h.empty:
            res.allowed = False
            res.block_reason = "EMPTY_DATA"
            return res
            
        last_row = df_1h.iloc[-1]
        
        # 1. EMA50 Direction Filter
        close_val = Decimal(str(last_row['close']))
        ema_val = Decimal(str(last_row['ema50']))
        slope_val = Decimal(str(last_row.get('ema50_slope', 0)))
        slope_threshold = Decimal(str(config.get("ema50_slope_threshold", "0.0003")))
        
        # New V7 specific thresholds
        long_min_slope = Decimal(str(config.get("long_min_ema_slope", "0.0003")))
        long_min_px_ema = Decimal(str(config.get("long_min_price_vs_ema", "0.005")))
        short_max_slope = Decimal(str(config.get("short_max_ema_slope", "-0.0003")))
        short_max_px_ema = Decimal(str(config.get("short_max_price_vs_ema", "-0.005")))

        res.close_1h = close_val
        res.ema50_1h = ema_val
        res.ema50_slope = slope_val
        res.close_vs_ema50_pct = (close_val - ema_val) / ema_val * 100 if ema_val > 0 else Decimal("0")
        
        px_threshold_long = ema_val * (Decimal("1") + long_min_px_ema)
        px_threshold_short = ema_val * (Decimal("1") + short_max_px_ema)

        if attempted_side == "LONG":
            # BLOCK ONLY IF (Bad Price) AND (Bad Slope)
            is_bad_price = close_val < px_threshold_long
            is_bad_slope = slope_val < long_min_slope
            
            if is_bad_price and is_bad_slope:
                res.allowed = False
                res.filter_type = "EMA50_DIRECTION"
                res.block_reason = REASON_EMA_LONG_BLOCKED
        else: # SHORT
            # BLOCK ONLY IF (Bad Price) AND (Bad Slope)
            is_bad_price = close_val > px_threshold_short
            is_bad_slope = slope_val > short_max_slope

            if is_bad_price and is_bad_slope:
                res.allowed = False
                res.filter_type = "EMA50_DIRECTION"
                res.block_reason = REASON_EMA_SHORT_BLOCKED
                
        if not res.allowed:
            return res

        # 2. Volatility State Filter
        vol_col = 'realized_vol_1h'
        if vol_col not in df_1h.columns:
            return res
            
        current_vol = last_row[vol_col]
        res.realized_vol_1h = Decimal(str(current_vol))
        
        # Percentile 90d (configurable window)
        window = int(config.get("volatility_window_bars", 2160))
        vol_history = df_1h[vol_col].tail(window)
        if len(vol_history) > 0:
            vol_pct = (vol_history < current_vol).mean() * 100
        else:
            vol_pct = 50.0
            
        res.vol_percentile_90d = Decimal(str(vol_pct))
        
        # Determine Regime thresholds
        shock_threshold = float(config.get("volatility_shock_percentile", 90.0))
        high_vol_threshold = float(config.get("volatility_high_percentile", 70.0))
        low_vol_threshold = float(config.get("volatility_low_percentile", 10.0))
        min_dist_atr_low_vol = Decimal(str(config.get("min_breakout_dist_atr_low_vol", "0.15")))

        if vol_pct >= shock_threshold:
            res.vol_state = "SHOCK"
            res.allowed = False
            res.filter_type = "VOLATILITY_STATE"
            res.block_reason = REASON_SHOCK_BLOCKED
        elif vol_pct >= high_vol_threshold:
            res.vol_state = "HIGH_VOL"
        elif vol_pct > low_vol_threshold:
            res.vol_state = "NORMAL"
        else:
            res.vol_state = "LOW_VOL"
            # Block only if breakout_distance_atr < threshold
            dist_atr = breakout_res.breakout_distance_atr
            if dist_atr < min_dist_atr_low_vol:
                res.allowed = False
                res.filter_type = "VOLATILITY_STATE"
                res.block_reason = REASON_LOW_VOL_BLOCKED
                
        return res

    def get_current_regime(self, df_1h: pd.DataFrame) -> str:
        # Simple extraction for scanner
        res = self.check(df_1h, "LONG", BreakoutResult(breakout_distance_atr=Decimal("1.0")), {})
        return res.vol_state

    async def save_log(self, result: ContextFilterResult, event_id: int, run_id: int, db: Session):
        # Implementation for database log
        pass
