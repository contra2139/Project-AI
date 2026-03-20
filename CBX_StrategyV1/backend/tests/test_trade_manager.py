import sys
import os
from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

# Mock DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.trade_manager import TradeManager, TradeAction
from app.models.trade import Trade
from app.models.events import CompressionEvent

def run_tests():
    tm = TradeManager()
    zone = CompressionEvent(high=Decimal("50050"), low=Decimal("49950"))
    config = {
        "time_stop_bars": 8,
        "partial_exit_r_level": "1.0",
        "partial_exit_pct": "0.50"
    }

    print("🚀 Bắt đầu test Trade Manager (8 Cases)...\n")

    # Helper to create mock trade
    def create_trade(side="LONG", entry=50000, sl=49900, tp1=50100, partial=False):
        trade = Trade(
            trade_id=uuid4(),
            expansion_id=uuid4(),
            run_id=uuid4(),
            symbol_id=uuid4(),
            side=side,
            entry_model="FOLLOW_THROUGH",
            entry_time=datetime.utcnow(),
            entry_price=Decimal(str(entry)),
            stop_loss_price=Decimal(str(sl)),
            tp1_price=Decimal(str(tp1)),
            initial_risk_r_price=abs(Decimal(str(entry)) - Decimal(str(sl))),
            position_size=Decimal("1.0"),
            position_size_usd=Decimal("50000"),
            risk_amount_usd=Decimal("100"),
            status="OPEN",
            partial_exit_done=partial,
            hold_bars=0,
            MFE_r=Decimal("0"),
            MAE_r=Decimal("0")
        )
        return trade

    # Test 1: STOP_LOSS triggered LONG
    t1 = create_trade()
    bar1 = {'low': Decimal("49850"), 'high': Decimal("50050"), 'close': Decimal("50000")}
    res1 = tm.update(t1, bar1, zone, config)
    print(f"Test 1 (SL LONG): {'✅ PASS' if res1.action_type == 'CLOSE_FULL' and res1.exit_type == 'STOP_LOSS' else '❌ FAIL'}")

    # Test 2: STOP_LOSS triggered SHORT
    t2 = create_trade(side="SHORT", entry=50000, sl=50100, tp1=49900)
    bar2 = {'low': Decimal("49950"), 'high': Decimal("50150"), 'close': Decimal("50000")}
    res2 = tm.update(t2, bar2, zone, config)
    print(f"Test 2 (SL SHORT): {'✅ PASS' if res2.action_type == 'CLOSE_FULL' and res2.exit_type == 'STOP_LOSS' else '❌ FAIL'}")

    # Test 3: STRUCTURE_FAIL LONG (Price < Zone low)
    t3 = create_trade()
    bar3 = {'low': Decimal("49960"), 'high': Decimal("50040"), 'close': Decimal("49940")} # close < 49950
    res3 = tm.update(t3, bar3, zone, config)
    print(f"Test 3 (Struct Fail): {'✅ PASS' if res3.action_type == 'CLOSE_FULL' and res3.exit_type == 'STRUCTURE_FAIL' else '❌ FAIL'}")

    # Test 4: TIME_STOP FIRED (hold_bars=8, pnl_r=0.3 < 1.0)
    t4 = create_trade()
    t4.hold_bars = 8
    bar4 = {'low': Decimal("49960"), 'high': Decimal("50050"), 'close': Decimal("50030")}
    # PnL R = (50030-50000)/100 = 0.3 < 1.0
    res4 = tm.update(t4, bar4, zone, config)
    print(f"Test 4 (Time Stop Fired): {'✅ PASS' if res4.action_type == 'CLOSE_FULL' and res4.exit_type == 'TIME_STOP' else '❌ FAIL'}")

    # Test 5: TIME_STOP NOT FIRED (hold_bars=8, pnl_r=1.2 > 1.0) -> action=HOLD
    t5 = create_trade()
    t5.hold_bars = 8
    t5.partial_exit_done = True # Already partialed, so don't fire PARTIAL_1R again
    bar5 = {'low': Decimal("50050"), 'high': Decimal("50150"), 'close': Decimal("50120")}
    # PnL R = (50120-50000)/100 = 1.2 > 1.0
    res5 = tm.update(t5, bar5, zone, config)
    print(f"Test 5 (Time Stop Not Fired): {'✅ PASS' if res5.action_type == 'HOLD' else '❌ FAIL'}")

    # Test 6: PARTIAL_1R FIRED
    t6 = create_trade()
    t6.partial_exit_done = False
    bar6 = {'low': Decimal("50000"), 'high': Decimal("50105"), 'close': Decimal("50080")}
    # high 50105 >= tp1 50100
    res6 = tm.update(t6, bar6, zone, config)
    print(f"Test 6 (Partial 1R): {'✅ PASS' if res6.action_type == 'CLOSE_PARTIAL' and res6.exit_type == 'PARTIAL_1R' else '❌ FAIL'} | Size: {res6.size_to_close}")

    # Test 7: TRAILING hit after partial
    t7 = create_trade(partial=True)
    t7.trailing_stop_price = Decimal("50020")
    bar7 = {'low': Decimal("50015"), 'high': Decimal("50100"), 'close': Decimal("50050")}
    # low 50015 <= trailing 50020
    res7 = tm.update(t7, bar7, zone, config)
    print(f"Test 7 (Trailing SL): {'✅ PASS' if res7.action_type == 'CLOSE_FULL' and res7.exit_type == 'TRAILING' else '❌ FAIL'}")

    # Test 8: HOLD + MFE/MAE update
    t8 = create_trade()
    t8.hold_bars = 3
    bar8 = {'low': Decimal("49920"), 'high': Decimal("50080"), 'close': Decimal("50010")}
    # MAE R = |50000-49920|/100 = 0.8
    # MFE R = |50080-50000|/100 = 0.8
    res8 = tm.update(t8, bar8, zone, config)
    tm.update_mfe_mae(t8, bar8)
    print(f"Test 8 (Hold + Metrics): {'✅ PASS' if res8.action_type == 'HOLD' and t8.MFE_r == Decimal('0.8') and t8.MAE_r == Decimal('0.8') else '❌ FAIL'}")

if __name__ == "__main__":
    run_tests()
