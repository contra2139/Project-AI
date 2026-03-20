import sys
import os
from decimal import Decimal
import pandas as pd
from datetime import datetime, timedelta

# Mock DATABASE_URL for app.database import
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.expansion_validator import ExpansionValidator
from app.strategy.breakout_detector import BreakoutResult
from app.models.events import CompressionEvent

def create_mock_bar(open=50000, high=50100, low=49950, close=50080):
    timestamp = int(datetime.now().timestamp() * 1000)
    return {
        'timestamp': timestamp,
        'open': Decimal(str(open)),
        'high': Decimal(str(high)),
        'low': Decimal(str(low)),
        'close': Decimal(str(close))
    }

def run_tests():
    validator = ExpansionValidator()
    config = {
        "expansion_body_loss_max_pct": 50,
        "expansion_lookforward_bars": 3
    }
    
    zone = CompressionEvent(high=50050, low=49950)
    
    # Base breakout bar (LONG)
    # Open 50040, High 50120, Low 50030, Close 50110 (Body 70, Range 90)
    # ATR inferred from Range 90 / bar_size_atr 0.9 = 100
    breakout_bar = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'open': Decimal("50040"),
        'high': Decimal("50120"),
        'low': Decimal("50030"),
        'close': Decimal("50110")
    }
    
    breakout_res = BreakoutResult(
        is_valid=True,
        side="LONG",
        breakout_price_level=Decimal("50050"),
        bar_size_atr=Decimal("0.9"), # implies ATR 100
        breakout_bar=breakout_bar
    )

    print("🚀 Bắt đầu test Expansion Validator (9 Cases)...\n")

    # Test 1: LONG confirmed — Condition A
    bars1 = [create_mock_bar(open=50110, high=50150, low=50105, close=50140)] # High 50150 > 50120
    res1 = validator.validate(breakout_res, bars1, zone, config)
    print(f"Test 1 (LONG A): {'✅ PASS' if res1.is_confirmed and res1.confirmed_by == 'CONDITION_A' else '❌ FAIL'} | Confirmed index: {res1.confirmation_bar_index}")

    # Test 2: LONG confirmed — Condition B (bar 2)
    # Bar 1: Hold (no HH)
    # Bar 2: Hold -> Confirm
    bars2 = [
        create_mock_bar(open=50110, high=50115, low=50095, close=50100), 
        create_mock_bar(open=50100, high=50110, low=50095, close=50100)
    ]
    res2 = validator.validate(breakout_res, bars2, zone, config)
    print(f"Test 2 (LONG B): {'✅ PASS' if res2.is_confirmed and res2.confirmed_by == 'CONDITION_B' and res2.confirmation_bar_index == 2 else '❌ FAIL'} | Confirmed index: {res2.confirmation_bar_index}")

    # Test 3: LONG rejected — REENTRY_DEEP
    bars3 = [create_mock_bar(open=50110, high=50115, low=50040, close=50045)] # Close < 50050
    res3 = validator.validate(breakout_res, bars3, zone, config)
    print(f"Test 3 (REENTRY): {'✅ PASS' if not res3.is_confirmed and 'REENTRY_DEEP' in res3.rejection_reasons else '❌ FAIL'} | Reasons: {res3.rejection_reasons}")

    # Test 4: LONG rejected — BODY_LOSS_EXCEEDED
    # Body Size = 110-40 = 70. Loss 50% = 35. Breakout Close 50110. 
    # Must stay above 50110 - 35 = 50075.
    # Set Low = 50070 (Loss = 40/70 = 57%)
    bars4 = [create_mock_bar(open=50110, high=50115, low=50070, close=50090)]
    res4 = validator.validate(breakout_res, bars4, zone, config)
    print(f"Test 4 (BODY LOSS): {'✅ PASS' if not res4.is_confirmed and 'BODY_LOSS_EXCEEDED' in res4.rejection_reasons else '❌ FAIL'} | Reasons: {res4.rejection_reasons}")

    # Test 5: LONG rejected — NO_FOLLOWTHROUGH
    # Bar 1: No confirm, no reject.
    # config setup lookforward = 1 to trigger timeout in Bar 1? No, default 3.
    # Let's provide 3 bars that don't satisfy A or B.
    # Wait, Condition B confirms on Bar 2. So to get NO_FOLLOWTHROUGH we need to fail earlier?
    # Actually B triggers on Bar 2 because if we reach Bar 2 without rejection, it means we "held".
    # So NO_FOLLOWTHROUGH only happens if bars < 2? No, NO_FOLLOWTHROUGH is a timeout.
    # If config setup lookforward=3, but we only have 1 bar and it doesn't satisfy A.
    res5 = validator.validate(breakout_res, bars1[:1], zone, {"expansion_lookforward_bars": 3})
    # Condition A would have triggered in bars1. Let's make one that doesn't.
    bars5 = [create_mock_bar(open=50110, high=50115, low=50080, close=50090)]
    res5 = validator.validate(breakout_res, bars5, zone, {"expansion_lookforward_bars": 1})
    print(f"Test 5 (TIMEOUT): {'✅ PASS' if not res5.is_confirmed and 'NO_FOLLOWTHROUGH' in res5.rejection_reasons else '❌ FAIL'} | Reasons: {res5.rejection_reasons}")

    # --- SHORT CASES ---
    # Open 49960, Close 49890 (Body 70, Range 90). Price level 49950. ATR 100.
    breakout_bar_short = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'open': Decimal("49960"),
        'high': Decimal("49970"),
        'low': Decimal("49880"),
        'close': Decimal("49890")
    }
    breakout_res_short = BreakoutResult(
        is_valid=True,
        side="SHORT",
        breakout_price_level=Decimal("49950"),
        bar_size_atr=Decimal("0.9"),
        breakout_bar=breakout_bar_short
    )

    # Test 6: SHORT confirmed — Condition A
    bars6 = [create_mock_bar(open=49890, high=49895, low=49800, close=49810)] # Low 49800 < 49880
    res6 = validator.validate(breakout_res_short, bars6, zone, config)
    print(f"Test 6 (SHORT A): {'✅ PASS' if res6.is_confirmed and res6.confirmed_by == 'CONDITION_A' else '❌ FAIL'} | Confirmed index: {res6.confirmation_bar_index}")

    # Test 7: SHORT confirmed — Condition B
    bars7 = [
        create_mock_bar(open=49890, high=49910, low=49885, close=49900),
        create_mock_bar(open=49900, high=49920, low=49895, close=49910)
    ]
    res7 = validator.validate(breakout_res_short, bars7, zone, config)
    print(f"Test 7 (SHORT B): {'✅ PASS' if res7.is_confirmed and res7.confirmed_by == 'CONDITION_B' else '❌ FAIL'} | Confirmed index: {res7.confirmation_bar_index}")

    # Test 8: SHORT rejected — REENTRY_DEEP
    bars8 = [create_mock_bar(open=49890, high=49960, low=49885, close=49955)] # Close > 49950
    res8 = validator.validate(breakout_res_short, bars8, zone, config)
    print(f"Test 8 (REENTRY SHORT): {'✅ PASS' if not res8.is_confirmed and 'REENTRY_DEEP' in res8.rejection_reasons else '❌ FAIL'} | Reasons: {res8.rejection_reasons}")

    # Test 9: Max extension Calculation
    # Level 50000, Max High 50300, ATR 200 -> 1.5 ATR
    br9 = BreakoutResult(
        is_valid=True, side="LONG", breakout_price_level=Decimal("50000"),
        bar_size_atr=Decimal("0.5"), # Range 100 / ATR 200 = 0.5
        breakout_bar={'high': Decimal("50100"), 'low': Decimal("50000"), 'open': Decimal("50000"), 'close': Decimal("50100")}
    )
    bars9 = [create_mock_bar(high=50300, close=50250, low=50150)]
    res9 = validator.validate(br9, bars9, zone, config)
    print(f"Test 9 (Metric 1.5 ATR): {'✅ PASS' if res9.max_extension_atr == Decimal('1.5') else '❌ FAIL'} | ATR: {res9.max_extension_atr}")

if __name__ == "__main__":
    run_tests()
