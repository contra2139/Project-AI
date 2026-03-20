import pandas as pd
from decimal import Decimal
from typing import Optional, Dict, Any, List
from app.models.symbol import SymbolStrategyConfig
from app.models.events import CompressionEvent
from datetime import datetime
import uuid

class CompressionDetector:
    """
    CompressionDetector identifies periods of low volatility (Compression)
    based on percentile signals.
    """

    def detect(self, df: pd.DataFrame, run_id: uuid.UUID, symbol_id: uuid.UUID, config: dict) -> Optional[CompressionEvent]:
        """
        Detects if the most recent bars in df form an active compression zone.
        Rebuilds state from the provided dataframe (df).
        """
        if df.empty:
            return None

        # parameters
        atr_thresh = float(config.get('atr_percentile_threshold', 20.0))
        range_thresh = float(config.get('range_percentile_threshold', 20.0))
        bbw_thresh = float(config.get('bb_width_percentile_threshold', 20.0))
        vol_thresh = float(config.get('volume_percentile_threshold', 60.0))
        min_cond = int(config.get('min_conditions_met', 3))
        min_bars = int(config.get('compression_min_bars', 8))
        max_bars = int(config.get('compression_max_bars', 24))

        # We look backwards from the end to find the start of the current compression
        bars = df.to_dict('records')
        active_zone = None
        
        # Simple implementation: start from end and walk back
        # But for correctness, we should walk forward to handle max_bars and resets
        current_zone = None
        
        for i, row in enumerate(bars):
            # Check conditions for this bar
            atr_pct = float(row.get('atr_norm_pct', 100.0))
            range_pct = float(row.get('range_pct_pct', 100.0))
            bbw_pct = float(row.get('bb_width_pct', 100.0))
            vol_pct = float(row.get('vol_ratio_pct', 100.0))
            
            met = 0
            if atr_pct <= atr_thresh: met += 1
            if range_pct <= range_thresh: met += 1
            if bbw_pct <= bbw_thresh: met += 1
            if vol_pct <= vol_thresh: met += 1
            
            is_compressed = met >= min_cond
            
            if is_compressed:
                if current_zone is None:
                    # Start new zone
                    current_zone = {
                        "start_index": i,
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "count": 1
                    }
                else:
                    # Update current
                    current_zone["high"] = max(current_zone["high"], float(row['high']))
                    current_zone["low"] = min(current_zone["low"], float(row['low']))
                    current_zone["count"] += 1
                    # If exceeding max_bars, we could truncate or reset
                    # Requirement says max_bars is usually for validity, but let's keep it simple
            else:
                # Compression broken
                current_zone = None
        
        if current_zone and current_zone["count"] >= min_bars:
            # Return as a CompressionEvent (mock or actual)
            # In Scanner, we'll convert this to a DB model if needed
            # For now, return the dict or an object
            last_bar = bars[-1]
            start_bar = bars[current_zone["start_index"]]
            return CompressionEvent(
                event_id=uuid.uuid4(),
                symbol_id=symbol_id,
                run_id=run_id,
                timeframe="15m",
                start_time=start_bar.get('timestamp') or datetime.utcnow(),
                end_time=last_bar.get('timestamp') or datetime.utcnow(),
                high=Decimal(str(current_zone["high"])),
                low=Decimal(str(current_zone["low"])),
                bar_count=current_zone["count"],
                width_pct=Decimal(str(last_bar.get('bb_width', 0))),
                width_atr_ratio=Decimal("0"),
                atr_value=Decimal(str(last_bar.get('atr', 1))),
                atr_percentile=Decimal(str(last_bar.get('atr_norm_pct', 0))),
                range_percentile=Decimal(str(last_bar.get('range_pct_pct', 0))),
                bb_width_percentile=Decimal(str(last_bar.get('bb_width_pct', 0))),
                vol_percentile=Decimal(str(last_bar.get('vol_ratio_pct', 0))),
                conditions_met=min_cond,
                false_break_count=0,
                quality_score=Decimal("0"),
                is_active=True,
                is_valid=True
            )
            
        return None
