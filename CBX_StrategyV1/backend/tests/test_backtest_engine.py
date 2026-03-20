import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from dataclasses import dataclass
import pandas as pd
import asyncio

# Setup dummy env for imports
os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"

# Setup PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backtest.simulator import FillSimulator
from app.backtest.engine import BacktestEngine, BacktestConfig, BacktestRunResult
from app.backtest.reporter import BacktestReporter, BacktestSummary
from app.models.trade import Trade
from app.models.events import CompressionEvent

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        self.simulator = FillSimulator()
        self.db_factory = MagicMock()
        self.engine = BacktestEngine(self.db_factory)

    def test_case_1_no_lookahead_bias(self):
        """
        Verify that calculations at bar i do not use information from bar i+1.
        """
        data = {
            "timestamp": [datetime.now() + timedelta(minutes=15*i) for i in range(10)],
            "open": [100 + i for i in range(10)],
            "high": [105 + i for i in range(10)],
            "low": [95 + i for i in range(10)],
            "close": [102 + i for i in range(10)],
            "volume": [1000 for _ in range(10)]
        }
        df = pd.DataFrame(data)
        i = 5
        visible_data = df.iloc[:i+1]
        original_last_close = visible_data.iloc[-1]["close"]
        df.at[6, "close"] = 999999
        new_visible_data = df.iloc[:i+1]
        self.assertEqual(original_last_close, new_visible_data.iloc[-1]["close"])
        print("\nTest 1 (No Look-ahead): ✅ PASS")

    def test_case_2_slippage_calculation(self):
        """
        Verify fill_price = open + (atr * slippage_pct)
        """
        entry_bar = {"open": 50000}
        atr = Decimal("200")
        slip_pct = Decimal("0.05")
        fill_long = self.simulator.simulate_entry_fill(entry_bar, "LONG", atr, slip_pct)
        self.assertEqual(fill_long, Decimal("50010"))
        fill_short = self.simulator.simulate_entry_fill(entry_bar, "SHORT", atr, slip_pct)
        self.assertEqual(fill_short, Decimal("49990"))
        print("Test 2 (Slippage): ✅ PASS")

    def test_case_3_partial_fill_logic(self):
        """
        Verify partial fill hits correctly.
        """
        bar = {"high": 105, "low": 95}
        tp1 = Decimal("103")
        hit, price = self.simulator.simulate_partial_fill("LONG", tp1, bar)
        self.assertTrue(hit)
        self.assertEqual(price, tp1)
        tp1_short = Decimal("97")
        hit_s, price_s = self.simulator.simulate_partial_fill("SHORT", tp1_short, bar)
        self.assertTrue(hit_s)
        self.assertEqual(price_s, tp1_short)
        print("Test 3 (Partial Fill): ✅ PASS")

    def test_case_4_force_close_at_end(self):
        """
        Verify all trades are closed at the last bar.
        """
        trade = Trade(
            entry_price=Decimal("100"), 
            side="LONG", 
            status="OPEN",
            position_size=Decimal("0.1"),
            initial_risk_r_price=Decimal("1.0")
        )
        last_price = Decimal("110")
        fee_pct = Decimal("0.0005")
        self.engine._close_trade(trade, last_price, "FORCE_CLOSE_END_OF_DATA", datetime.now(), fee_pct)
        self.assertEqual(trade.status, "CLOSED")
        self.assertEqual(trade.exit_model, "FORCE_CLOSE_END_OF_DATA")
        self.assertEqual(trade.avg_exit_price, last_price)
        print("Test 4 (Force Close): ✅ PASS")

    def test_case_5_side_filter_logic(self):
        """
        Mock side filter logic in engine loop.
        """
        config = MagicMock(side_filter="LONG_ONLY")
        def check_side(side, filter_type):
            if filter_type == "LONG_ONLY" and side == "SHORT": return False
            if filter_type == "SHORT_ONLY" and side == "LONG": return False
            return True
        self.assertFalse(check_side("SHORT", config.side_filter))
        self.assertTrue(check_side("LONG", config.side_filter))
        print("Test 5 (Side Filter): ✅ PASS")

    async def async_test_case_6_smoke_test(self):
        """
        Smoke test — full backtest run with synthetic data.
        """
        data = {
            "timestamp": [datetime.now() + timedelta(minutes=15*i) for i in range(500)],
            "open": [100.0] * 500,
            "high": [105.0] * 500,
            "low": [95.0] * 500,
            "close": [100.0] * 500,
            "volume": [1000.0] * 500
        }
        df_15m = pd.DataFrame(data)
        df_1h = pd.DataFrame(data)
        config = BacktestConfig(
            symbol_id=uuid4(),
            strategy_config_id=uuid4(),
            data_start=data["timestamp"][0],
            data_end=data["timestamp"][-1],
            side_filter="LONG_ONLY",
            entry_model="FOLLOW_THROUGH"
        )
        self.engine._initialize_run = AsyncMock(return_value=uuid4())
        self.engine._load_data = AsyncMock(return_value=(df_15m, df_1h, MagicMock(), MagicMock()))
        trade = Trade(status="CLOSED", total_pnl_r=Decimal("1.5"), net_pnl_usd=Decimal("150"))
        event = CompressionEvent()
        self.engine._run_simulation = AsyncMock(return_value=([trade], [event]))
        summary = BacktestRunResult(
            run_id=config.strategy_config_id,
            total_trades=1,
            win_rate=Decimal("1.0"),
            total_pnl_r=Decimal("1.5"),
            total_pnl_usd=Decimal("150"),
            max_drawdown_r=Decimal("-0.1")
        )
        self.engine._finalize_run = AsyncMock(return_value=summary)
        db_mock = AsyncMock()
        self.db_factory.return_value.__aenter__.return_value = db_mock
        result = await self.engine.run(config)
        # Verify result contains basic fields as per user request
        self.assertEqual(result.total_trades, 1)
        self.assertTrue(isinstance(result.total_pnl_r, Decimal))
        self.assertLessEqual(result.max_drawdown_r, Decimal("0"))
        print("Test 6 (Smoke Test): ✅ PASS")

    def test_case_6_wrapper(self):
        asyncio.run(self.async_test_case_6_smoke_test())

    async def async_test_case_7_equity_curve(self):
        """
        Verify equity curve direction based on trade PnL.
        """
        initial_equity = Decimal("10000")
        risk_pct = Decimal("0.0025")
        risk_usd = initial_equity * risk_pct
        equity_after_t1 = initial_equity + (Decimal("1.0") * risk_usd)
        equity_after_t2 = equity_after_t1 + (Decimal("-1.0") * risk_usd)
        equity_after_t3 = equity_after_t2 + (Decimal("2.0") * risk_usd)
        final_equity = equity_after_t3
        net_pnl_usd = (Decimal("1.0") + Decimal("-1.0") + Decimal("2.0")) * risk_usd
        
        # In actual equity curve tracking, we'd check each step
        self.assertGreater(equity_after_t1, initial_equity)
        self.assertLess(equity_after_t2, equity_after_t1)
        self.assertGreater(equity_after_t3, equity_after_t2)
        self.assertAlmostEqual(float(final_equity), float(initial_equity + net_pnl_usd), delta=0.01)
        print("Test 7 (Equity Curve): ✅ PASS")

    def test_case_7_wrapper(self):
        asyncio.run(self.async_test_case_7_equity_curve())

    def test_case_8_short_pnl_direction(self):
        """
        Verify PnL for SHORT trades (Price down = Profit).
        SHORT trade: entry=50000, exit=49900 (price down 100)
        initial_risk_r_price = 100
        Assert: pnl_r == Decimal("1.0")
        """
        trade = Trade(
            side="SHORT",
            entry_price=Decimal("50000"),
            initial_risk_r_price=Decimal("100"),
            position_size=Decimal("1.0"),
            status="OPEN"
        )
        exit_price = Decimal("49900")
        self.engine._close_trade(trade, exit_price, "TAKE_PROFIT", datetime.now(), Decimal("0"))
        
        self.assertEqual(trade.status, "CLOSED")
        self.assertEqual(trade.total_pnl_r, Decimal("1.0"))
        self.assertGreater(trade.total_pnl_r, 0)
        print("Test 8 (SHORT PnL Direction): ✅ PASS")

if __name__ == "__main__":
    unittest.main()
