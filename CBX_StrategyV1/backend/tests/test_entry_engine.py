import sys
import os
from decimal import Decimal
from datetime import datetime

# Mock DATABASE_URL for app.database import
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.entry_engine import EntryEngine, EntryOrder
from app.strategy.breakout_detector import BreakoutResult
from app.strategy.expansion_validator import ExpansionResult
from app.models.events import CompressionEvent

def run_tests():
    engine = EntryEngine()
    zone = CompressionEvent(high=Decimal("50050"), low=Decimal("49950"), atr_value=Decimal("100"))
    setattr(zone, 'symbol', 'BTCUSDC')
    
    breakout_bar = {
        'open': Decimal("50040"),
        'high': Decimal("50120"),
        'low': Decimal("50030"),
        'close': Decimal("50110")
    }
    
    breakout_res = BreakoutResult(
        is_valid=True,
        side="LONG",
        breakout_bar=breakout_bar
    )
    
    expansion_res = ExpansionResult(is_confirmed=True, confirmed_by="CONDITION_A")
    config = {"retest_max_bars": 3}
    
    print("🚀 Bắt đầu test Entry Engine (5 Cases)...\n")

    # Test 1: FT entry valid
    res1 = engine.prepare_entry(expansion_res, breakout_res, zone, "FOLLOW_THROUGH", config, Decimal("49950"))
    print(f"Test 1 (FT Entry): {'✅ PASS' if res1.is_valid and res1.entry_price_estimate == Decimal('50110') else '❌ FAIL'}")

    # Test 2: RT entry valid (preparation only)
    res2 = engine.prepare_entry(expansion_res, breakout_res, zone, "RETEST", config, Decimal("49950"))
    print(f"Test 2 (RT Entry): {'✅ PASS' if res2.is_valid and res2.entry_price_estimate == Decimal('50050') else '❌ FAIL'}")

    # Test 3: RT Timeout — RETEST_TIMEOUT
    # Create a fresh RETEST order
    order3 = engine.prepare_entry(expansion_res, breakout_res, zone, "RETEST", config, Decimal("49950"))
    # Simulate 4 bars (max is 3) without retest
    # Price stays high (no retest to 50050 ± 5)
    bar_high = {'high': Decimal("50200"), 'low': Decimal("50150"), 'close': Decimal("50180")}
    for _ in range(4):
        engine.update_order_status(order3, bar_high, zone, config)
    
    print(f"Test 3 (RT Timeout): {'✅ PASS' if not order3.is_valid and order3.invalid_reason == 'RETEST_TIMEOUT' else '❌ FAIL'} | Reason: {order3.invalid_reason}")

    # Test 4: is_still_valid=False (Too Far)
    curr_bar4 = {'close': Decimal("50300")} # dist to 50110 (FT) is 190 > 150
    valid4 = engine.is_still_valid(res1, curr_bar4, zone, Decimal("100"))
    print(f"Test 4 (Still Valid - False): {'✅ PASS' if not valid4 else '❌ FAIL'}")

    # Test 5: is_still_valid=True (Inside 1.5 ATR buffer)
    curr_bar5 = {'close': Decimal("50150")} # dist to 50110 is 40 < 150
    valid5 = engine.is_still_valid(res1, curr_bar5, zone, Decimal("100"))
    print(f"Test 5 (Still Valid - True): {'✅ PASS' if valid5 else '❌ FAIL'}")

if __name__ == "__main__":
    run_tests()
