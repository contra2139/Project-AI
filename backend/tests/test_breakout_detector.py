import sys
import os
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mock DATABASE_URL for app.database import
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.breakout_detector import BreakoutDetector
from app.models.events import CompressionEvent

def create_mock_bar(open=50000, high=50100, low=49950, close=50080, vol=1000):
    timestamp = int(datetime.now().timestamp() * 1000)
    return pd.Series({
        'timestamp': timestamp,
        'open': open,
        'high': high,
        'low': low,
        'close': close,
        'volume': vol
    })

def create_mock_features(atr=100, vol_ratio=1.5, vol_pct=75):
    return pd.Series({
        'atr': atr,
        'volume_ratio': vol_ratio,
        'volume_percentile': vol_pct
    })

def run_tests():
    detector = BreakoutDetector()
    config = {
        "false_break_limit": 2,
        "breakout_distance_min_atr": Decimal("0.20"),
        "breakout_body_ratio_min": Decimal("0.60")
    }
    
    zone = CompressionEvent(
        high=50050,
        low=49950,
        false_break_count=0
    )
    
    print("🚀 Bắt đầu test Breakout Detector (8 Cases)...\n")
    
    # Test 1: LONG valid (All pass)
    bar1 = create_mock_bar(open=50040, high=50120, low=50030, close=50110, vol=2000) # Body 70, Range 90, Ratio 0.77
    feat1 = create_mock_features(atr=100, vol_ratio=1.5, vol_pct=80)
    res1 = detector.detect(bar1, zone, feat1, config)
    print(f"Test 1 (LONG valid): {'✅ PASS' if res1.is_valid else '❌ FAIL'} | Reasons: {res1.invalid_reasons}")

    # Test 2: LONG invalid (Body ratio 0.4)
    # Range: 50150-50030=120. Body: 50100-50052=48. Ratio: 48/120=0.4 (Min 0.6)
    bar2 = create_mock_bar(open=50052, high=50150, low=50030, close=50100)
    res2 = detector.detect(bar2, zone, feat1, config)
    print(f"Test 2 (LONG Body 0.4): {'✅ PASS' if not res2.is_valid and 'BODY_RATIO_TOO_LOW' in res2.invalid_reasons else '❌ FAIL'} | Reasons: {res2.invalid_reasons}")

    # Test 3: LONG invalid (Volume low)
    feat3 = create_mock_features(vol_ratio=0.7, vol_pct=45)
    res3 = detector.detect(bar1, zone, feat3, config)
    print(f"Test 3 (VOL low): {'✅ PASS' if not res3.is_valid and 'VOL_TOO_LOW' in res3.invalid_reasons else '❌ FAIL'} | Reasons: {res3.invalid_reasons}")

    # Test 4: LONG invalid (Size > 2.5 ATR)
    feat4 = create_mock_features(atr=50) # Range 90 / ATR 50 = 1.8 (Valid)
    bar4 = create_mock_bar(open=50040, high=50300, low=50030, close=50280) # Range 270 / 100 = 2.7
    res4 = detector.detect(bar4, zone, feat1, config)
    print(f"Test 4 (Size 2.7 ATR): {'✅ PASS' if not res4.is_valid and 'BAR_TOO_LARGE' in res4.invalid_reasons else '❌ FAIL'} | Reasons: {res4.invalid_reasons}")

    # Test 5: SHORT valid
    bar5 = create_mock_bar(open=49960, high=49970, low=49880, close=49890) # Range 90, Body 70, Close bottom
    res5 = detector.detect(bar5, zone, feat1, config)
    print(f"Test 5 (SHORT valid): {'✅ PASS' if res5.is_valid else '❌ FAIL'} | Status: {res5.side}")

    # Test 6: SHORT invalid (Close Pos 0.6)
    # Range: 49970-49850=120. Close 49898. Pos from top: (49970-49898)/120 = 72/120 = 0.6
    bar6 = create_mock_bar(open=49960, high=49970, low=49850, close=49898)
    res6 = detector.detect(bar6, zone, feat1, config)
    print(f"Test 6 (SHORT ClosePos 0.6): {'✅ PASS' if not res6.is_valid and 'CLOSE_POSITION' in res6.invalid_reasons else '❌ FAIL'} | Reasons: {res6.invalid_reasons}")

    # Test 7: LONG invalid (Wick dominant + Body ratio)
    # Open 50050, Close 50100 (Body 50). Low 50000 (Wick opposite 50). 
    # Range: 50110 - 49970 = 140. Body 50. Ratio: 50/140 = 0.357 (Fail Min 0.6)
    # Wick 50050-49970 = 80. Body 50 * 1.5 = 75. 80 > 75 (Fail Wick Dominant)
    bar7 = create_mock_bar(open=50050, high=50110, low=49970, close=50100)
    res7 = detector.detect(bar7, zone, feat1, config)
    expected_reasons = ['BODY_RATIO_TOO_LOW', 'WICK_DOMINANT']
    passed_test7 = all(r in res7.invalid_reasons for r in expected_reasons)
    print(f"Test 7 (Wick + Body): {'✅ PASS' if passed_test7 else '❌ FAIL'} | Reasons: {res7.invalid_reasons}")

    # Test 8: Banned (False breaks)
    zone8 = CompressionEvent(high=50050, low=49950, false_break_count=2)
    res8 = detector.detect(bar1, zone8, feat1, config)
    print(f"Test 8 (BANNED Limit): {'✅ PASS' if not res8.is_valid and 'BANNED_FALSE_BREAK_LIMIT' in res8.invalid_reasons else '❌ FAIL'} | Reasons: {res8.invalid_reasons}")

if __name__ == "__main__":
    run_tests()
