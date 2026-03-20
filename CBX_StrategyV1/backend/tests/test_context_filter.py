import sys
import os
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock DATABASE_URL for app.database import
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.context_filter import (
    ContextFilter, 
    REASON_EMA_LONG_BLOCKED, 
    REASON_EMA_SHORT_BLOCKED,
    REASON_SHOCK_BLOCKED,
    REASON_LOW_VOL_BLOCKED
)
from app.strategy.breakout_detector import BreakoutResult

def create_mock_df(count=3000, close_start=50000, ema50_start=49950, vol=0.005):
    # Historical data to fill 90 days (2160 bars)
    data = []
    curr_close = close_start
    curr_ema = ema50_start
    for i in range(count):
        # Add some noise
        curr_close += np.random.normal(0, 10)
        curr_ema = 0.98 * curr_ema + 0.02 * curr_close
        data.append({
            'timestamp': int(datetime.now().timestamp() * 1000) - (count - i) * 3600 * 1000,
            'close': curr_close,
            'ema50': curr_ema,
            'ema50_slope': 0, # To be determined per test
            'realized_vol_1h': vol + np.random.normal(0, 0.0001)
        })
    return pd.DataFrame(data).astype({
        'close': float,
        'ema50': float,
        'ema50_slope': float,
        'realized_vol_1h': float
    })

def run_tests():
    filter = ContextFilter()
    config = {
        "ema50_slope_threshold": "0.0003"
    }
    
    print("🚀 Bắt đầu test Context Filter (8 Cases)...\n")
    
    # Base Breakout
    br_normal = BreakoutResult(breakout_distance_atr=Decimal("0.20"))
    
    # Test 1: LONG allowed (Normal regime, close > EMA, slope flat)
    df1 = create_mock_df()
    df1.at[df1.index[-1], 'close'] = 50100
    df1.at[df1.index[-1], 'ema50'] = 50000
    df1.at[df1.index[-1], 'ema50_slope'] = 0
    df1.at[df1.index[-1], 'realized_vol_1h'] = 0.005
    res1 = filter.check(df1, "LONG", br_normal, config)
    print(f"Test 1 (LONG Normal): {'✅ PASS' if res1.allowed and res1.vol_state == 'NORMAL' else '❌ FAIL'}")

    # Test 2: LONG blocked (close < ema, slope strong negative)
    df2 = df1.copy()
    df2.at[df2.index[-1], 'close'] = 49900
    df2.at[df2.index[-1], 'ema50'] = 50000
    df2.at[df2.index[-1], 'ema50_slope'] = -0.001
    res2 = filter.check(df2, "LONG", br_normal, config)
    print(f"Test 2 (LONG Blocked EMA): {'✅ PASS' if not res2.allowed and res2.block_reason == REASON_EMA_LONG_BLOCKED else '❌ FAIL'} | Reason: {res2.block_reason}")

    # Test 3: SHORT allowed
    res3 = filter.check(df2, "SHORT", br_normal, config) # Still df2 (close < ema, slope negative)
    print(f"Test 3 (SHORT Normal): {'✅ PASS' if res3.allowed else '❌ FAIL'}")

    # Test 4: SHORT blocked (close > ema, slope positive)
    df4 = df1.copy()
    df4.at[df4.index[-1], 'close'] = 50100
    df4.at[df4.index[-1], 'ema50'] = 50000
    df4.at[df4.index[-1], 'ema50_slope'] = 0.001
    res4 = filter.check(df4, "SHORT", br_normal, config)
    print(f"Test 4 (SHORT Blocked EMA): {'✅ PASS' if not res4.allowed and res4.filter_type == 'EMA50_DIRECTION' else '❌ FAIL'}")

    # Test 5: BOTH blocked (SHOCK)
    df5 = df1.copy()
    df5.at[df5.index[-1], 'realized_vol_1h'] = 0.1 # Very high vol
    # Make sure history is low so current is high percentile
    df5.iloc[:-1, df5.columns.get_loc('realized_vol_1h')] = 0.001
    res5 = filter.check(df5, "LONG", br_normal, config)
    print(f"Test 5 (SHOCK Blocked): {'✅ PASS' if not res5.allowed and res5.block_reason == REASON_SHOCK_BLOCKED else '❌ FAIL'} | State: {res5.vol_state}")

    # Test 6: LOW_VOL blocked (breakout too small)
    df6 = df1.copy()
    df6.at[df6.index[-1], 'realized_vol_1h'] = 0.0001 # Low vol
    df6.iloc[:-1, df6.columns.get_loc('realized_vol_1h')] = 0.01 # History high
    # percentile will be ~0 (definitely <= 5.0)
    br6 = BreakoutResult(breakout_distance_atr=Decimal("0.10")) # < 0.15
    res6 = filter.check(df6, "LONG", br6, config)
    print(f"Test 6 (LOW_VOL Blocked): {'✅ PASS' if not res6.allowed and res6.block_reason == REASON_LOW_VOL_BLOCKED else '❌ FAIL'} | State: {res6.vol_state}")

    # Test 7: LOW_VOL allowed (breakout large enough)
    br7 = BreakoutResult(breakout_distance_atr=Decimal("0.20")) # >= 0.15
    res7 = filter.check(df6, "LONG", br7, config)
    print(f"Test 7 (LOW_VOL Allowed): {'✅ PASS' if res7.allowed and res7.vol_state == 'LOW_VOL' else '❌ FAIL'}")

    # Test 8: HIGH_VOL allowed
    df8 = df1.copy()
    # Current is high but not shock
    history_8 = np.linspace(0.001, 0.010, 2160)
    df8.iloc[-2161:-1, df8.columns.get_loc('realized_vol_1h')] = history_8
    df8.at[df8.index[-1], 'realized_vol_1h'] = 0.008 # between 70-90 percentile
    res8 = filter.check(df8, "LONG", br_normal, config)
    print(f"Test 8 (HIGH_VOL Allowed): {'✅ PASS' if res8.allowed and res8.vol_state == 'HIGH_VOL' else '❌ FAIL'} | Pct: {res8.vol_percentile_90d}")

if __name__ == "__main__":
    run_tests()
