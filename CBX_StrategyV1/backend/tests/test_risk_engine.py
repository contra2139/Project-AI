import sys
import os
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Mock DATABASE_URL for app.database import
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.strategy.risk_engine import RiskEngine
from app.models.session import SessionState
from app.models.events import CompressionEvent

async def run_tests():
    risk = RiskEngine()
    symbol_id = uuid4()
    run_id = uuid4()
    
    config = {
        "risk_per_trade_pct": "0.0025",
        "risk_daily_stop_r": "-2.0",
        "risk_consecutive_fail_stop": 3,
        "max_position_per_symbol": 1,
        "risk_max_positions_portfolio": 2,
        "stop_loss_atr_buffer": "0.25"
    }
    
    exchange_config = {
        "lot_size_step": "0.001",
        "min_qty": "0.001",
        "min_notional": "5.0"
    }

    print("🚀 Bắt đầu test Risk Engine (7 Cases)...\n")

    # Test 1: Position Size: qty=0.25 (equity=10000, risk=0.25%, distance=100)
    res1 = risk.calculate_position_size(
        entry_price=Decimal("50000"),
        stop_price=Decimal("49900"),
        equity_usd=Decimal("10000"),
        config=config,
        exchange_config=exchange_config
    )
    print(f"Test 1 (Position Size): {'✅ PASS' if res1.qty == Decimal('0.25') else '❌ FAIL'} | Qty: {res1.qty}")

    # Test 2: Lot Size Rounding: qty=0.256 (raw=0.2567, step=0.001)
    res2 = risk.calculate_position_size(
        entry_price=Decimal("50000"),
        stop_price=Decimal("49902"), # distance 98
        equity_usd=Decimal("10065"), # raw_qty = 25.1625 / 98 = 0.25676...
        config=config,
        exchange_config=exchange_config
    )
    print(f"Test 2 (Floor Rounding): {'✅ PASS' if res2.qty == Decimal('0.256') else '❌ FAIL'} | Qty: {res2.qty}")

    # Test 3: Min Qty Invalid: valid=False (rounded=0.0005, min=0.001)
    res3 = risk.calculate_position_size(
        entry_price=Decimal("50000"),
        stop_price=Decimal("45000"), # distance 5000
        equity_usd=Decimal("1000"),   # risk_amount = 2.5. Qty = 2.5/5000 = 0.0005
        config=config,
        exchange_config=exchange_config
    )
    print(f"Test 3 (Min Qty): {'✅ PASS' if not res3.valid and 'MIN_QTY' in res3.invalid_reason else '❌ FAIL'} | Valid: {res3.valid}")

    # --- check_can_trade Cases (Mocks) ---
    async def mock_db(session_obj):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session_obj
        mock_result.scalar.return_value = session_obj.open_position_count if session_obj else 0
        db.execute.return_value = mock_result
        return db

    # Test 4: Daily Stop Hit: allowed=False (daily_pnl_r = -2.1)
    session4 = SessionState(current_daily_pnl_r=Decimal("-2.1"), trading_halted=False)
    db4 = await mock_db(session4)
    res4 = await risk.check_can_trade(symbol_id, run_id, db4, config)
    print(f"Test 4 (Daily Stop): {'✅ PASS' if not res4.allowed and res4.block_reason == 'DAILY_STOP' else '❌ FAIL'}")

    # Test 5: Consecutive Fail Hit: allowed=False (failures = 3)
    session5 = SessionState(current_daily_pnl_r=Decimal("0"), consecutive_failures=3, trading_halted=False)
    db5 = await mock_db(session5)
    res5 = await risk.check_can_trade(symbol_id, run_id, db5, config)
    print(f"Test 5 (Consecutive Fail): {'✅ PASS' if not res5.allowed and res5.block_reason == 'CONSECUTIVE_FAIL' else '❌ FAIL'}")

    # Test 6: Max Position Symbol: allowed=False (count=1, max=1)
    session6 = SessionState(current_daily_pnl_r=Decimal("0"), consecutive_failures=0, open_position_count=1, trading_halted=False)
    db6 = await mock_db(session6)
    res6 = await risk.check_can_trade(symbol_id, run_id, db6, config)
    print(f"Test 6 (Max Pos Symbol): {'✅ PASS' if not res6.allowed and res6.block_reason == 'MAX_POSITION_SYMBOL' else '❌ FAIL'}")

    # Test 7: Stop Loss LONG (zone.high=50000, atr=200, buffer=0.25, bar.low=49950 -> stop=49950)
    zone7 = CompressionEvent(high=Decimal("50000"), low=Decimal("49800"), atr_value=Decimal("200"))
    bar7 = {'low': Decimal("49950")}
    # level_1 = 50000 - 0.25*200 = 49950. level_2 = 49950. stop = 49950.
    res7 = risk.calculate_stop_loss("LONG", zone7, bar7, config)
    print(f"Test 7 (Stop Loss LONG): {'✅ PASS' if res7 == Decimal('49950') else '❌ FAIL'} | Stop: {res7}")

    # Test 8: consecutive_failures reset (trade_result="WIN")
    session8 = SessionState(
        consecutive_failures=2,
        open_position_count=1,
        current_daily_pnl_r=Decimal("0")
    )
    db8 = await mock_db(session8)
    # We need a custom mock for commit and scalar_one if we use full RiskEngine logic
    # But update_session_on_close uses select(). scalar_one()
    # Let's adjust mock_db to return session8 on scalar_one() too
    db8.execute.return_value.scalar_one.return_value = session8
    
    await risk.update_session_on_close(symbol_id, run_id, Decimal("1.0"), "WIN", db8)
    print(f"Test 8 (Failures Reset): {'✅ PASS' if session8.consecutive_failures == 0 else '❌ FAIL'} | Fails: {session8.consecutive_failures}")

if __name__ == "__main__":
    asyncio.run(run_tests())
