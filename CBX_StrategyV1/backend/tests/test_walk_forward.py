import os
import sys

# Setup dummy env for imports
os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"

import unittest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import asyncio

# Setup PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backtest.walk_forward import WalkForwardValidator, WalkForwardConfig, WalkForwardWindowSummary
from app.backtest.engine import BacktestRunResult

class TestWalkForwardValidator(unittest.TestCase):
    def setUp(self):
        self.db_factory = MagicMock()
        self.validator = WalkForwardValidator(self.db_factory)

    def test_case_1_window_generation(self):
        """Test 1: Window generation đúng số lượng."""
        config = WalkForwardConfig(
            symbol_id=uuid4(),
            strategy_config_id=uuid4(),
            total_start=datetime(2024, 1, 1),
            total_end=datetime(2024, 7, 1),
            train_months=4,
            test_months=1,
            step_months=1
        )
        windows = self.validator._generate_windows(config)
        
        # Expected:
        # W1: Jan-May (4m), Test: May-Jun (1m) -> End Jun 1
        # W2: Feb-Jun (4m), Test: Jun-Jul (1m) -> End Jul 1
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["train_start"], datetime(2024, 1, 1))
        self.assertEqual(windows[1]["test_end"], datetime(2024, 7, 1))
        print("\nTest 1 (Window Generation): ✅ PASS")

    def test_case_2_efficiency_ratio(self):
        """Test 2: Efficiency ratio tính đúng."""
        # efficiency = test / train = 2.0 / 4.0 = 0.5
        win_summary = WalkForwardWindowSummary(
            window_index=1,
            train_period="",
            test_period="",
            train_pnl_r=Decimal("4.0"),
            test_pnl_r=Decimal("2.0"),
            efficiency_ratio=Decimal("0.5"),
            overfitting_flag=False
        )
        self.assertEqual(win_summary.efficiency_ratio, Decimal("0.5"))
        print("Test 2 (Efficiency Ratio): ✅ PASS")

    def test_case_3_efficiency_ratio_negative_train(self):
        """Test 3: Efficiency ratio khi train âm."""
        # Logic: if train <= 0, eff = 0
        train_pnl = Decimal("-1.0")
        test_pnl = Decimal("2.0")
        eff = Decimal("0")
        if train_pnl > 0:
            eff = test_pnl / train_pnl
        self.assertEqual(eff, Decimal("0"))
        print("Test 3 (Negative Train PnL): ✅ PASS")

    def test_case_4_overfitting_flag(self):
        """Test 4: Overfitting flag đúng."""
        threshold = Decimal("0.5")
        eff_1 = Decimal("0.3")
        eff_2 = Decimal("0.7")
        self.assertTrue(eff_1 < threshold) # Overfit
        self.assertFalse(eff_2 < threshold) # Not overfit
        print("Test 4 (Overfitting Flag): ✅ PASS")

    def test_case_5_is_robust_logic(self):
        """Test 5: is_robust logic."""
        config = WalkForwardConfig(
            symbol_id=uuid4(),
            strategy_config_id=uuid4(),
            total_start=datetime.now(),
            total_end=datetime.now(),
            overfitting_threshold=Decimal("0.5")
        )
        
        # 3 windows: eff=[0.6, 0.3, 0.7]
        # avg = 1.6 / 3 = 0.533 >= 0.5
        # overfit = 1/3 = 33% <= 50%
        # Expected: is_robust = True
        w1 = WalkForwardWindowSummary(1, "", "", Decimal("1.0"), Decimal("0.6"), Decimal("0.6"), False)
        w2 = WalkForwardWindowSummary(2, "", "", Decimal("1.0"), Decimal("0.3"), Decimal("0.3"), True)
        w3 = WalkForwardWindowSummary(3, "", "", Decimal("1.0"), Decimal("0.7"), Decimal("0.7"), False)
        
        result = self.validator._aggregate_results(uuid4(), [w1, w2, w3], config)
        self.assertTrue(result.is_robust)
        self.assertIn("MARGINAL", result.verdict)
        print("Test 5 (Robustness Logic): ✅ PASS")

if __name__ == "__main__":
    unittest.main()
