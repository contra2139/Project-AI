from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from uuid import UUID, uuid4
import asyncio
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.backtest.engine import BacktestEngine, BacktestConfig, BacktestRunResult
from app.models.run import WalkForwardWindow, ResearchRun

@dataclass
class WalkForwardConfig:
    symbol_id: UUID
    strategy_config_id: UUID
    total_start: datetime
    total_end: datetime
    train_months: int = 4
    test_months: int = 1
    step_months: int = 1
    side_filter: str = "BOTH" # LONG_ONLY, SHORT_ONLY, BOTH
    entry_model: str = "FOLLOW_THROUGH"
    initial_equity: Decimal = Decimal("10000")
    overfitting_threshold: Decimal = Decimal("0.5")
    experiment_name: str = "WFV_EXP"

@dataclass
class WalkForwardWindowSummary:
    window_index: int
    train_period: str
    test_period: str
    train_pnl_r: Decimal
    test_pnl_r: Decimal
    efficiency_ratio: Decimal
    overfitting_flag: bool

@dataclass
class WalkForwardResult:
    wf_experiment_id: UUID
    total_windows: int
    windows: List[WalkForwardWindowSummary]
    avg_train_pnl_r: Decimal
    avg_test_pnl_r: Decimal
    avg_efficiency_ratio: Decimal
    pct_overfitting_windows: Decimal
    profitable_windows: int
    losing_windows: int
    avg_out_pnl_r: Decimal
    is_robust: bool
    verdict: str

class WalkForwardValidator:
    """
    Validates strategy robustness using Walk-Forward analysis.
    Checks for overfitting by comparing In-Sample (Train) vs Out-of-Sample (Test) performance.
    """

    def __init__(self, db_factory):
        self.db_factory = db_factory
        self.engine = BacktestEngine(db_factory)

    async def run(self, config: WalkForwardConfig) -> WalkForwardResult:
        # 1. Generate Windows
        windows = self._generate_windows(config)
        if len(windows) < 2:
            raise ValueError("Insufficient data to create at least 2 windows.")

        wf_experiment_id = uuid4()
        window_summaries = []

        async with self.db_factory() as db:
            for window in windows:
                # IN-SAMPLE (Train)
                train_cfg = BacktestConfig(
                    symbol_id=config.symbol_id,
                    strategy_config_id=config.strategy_config_id,
                    data_start=window["train_start"],
                    data_end=window["train_end"],
                    run_name=f"{config.experiment_name}_W{window['window_index']}_TRAIN",
                    side_filter=config.side_filter,
                    entry_model=config.entry_model,
                    initial_equity=config.initial_equity
                )
                train_result = await self.engine.run(train_cfg)

                # OUT-OF-SAMPLE (Test)
                test_cfg = BacktestConfig(
                    symbol_id=config.symbol_id,
                    strategy_config_id=config.strategy_config_id,
                    data_start=window["test_start"],
                    data_end=window["test_end"],
                    run_name=f"{config.experiment_name}_W{window['window_index']}_TEST",
                    side_filter=config.side_filter,
                    entry_model=config.entry_model,
                    initial_equity=config.initial_equity
                )
                test_result = await self.engine.run(test_cfg)

                # Metrics (Revised Overfitting Logic)
                eff_ratio = Decimal("0")
                if train_result.total_pnl_r > 0:
                    eff_ratio = test_result.total_pnl_r / train_result.total_pnl_r
                
                # overfitting_flag = True ONLY if efficiency < 0.5 AND out-sample is negative
                overfit = (eff_ratio < config.overfitting_threshold) and (test_result.total_pnl_r < 0)

                # Save to DB
                wf_window = WalkForwardWindow(
                    wf_experiment_id=wf_experiment_id,
                    symbol_id=config.symbol_id,
                    window_index=window["window_index"],
                    train_start=window["train_start"],
                    train_end=window["train_end"],
                    test_start=window["test_start"],
                    test_end=window["test_end"],
                    train_run_id=train_result.run_id,
                    test_run_id=test_result.run_id,
                    train_pnl_r=train_result.total_pnl_r,
                    test_pnl_r=test_result.total_pnl_r,
                    train_win_rate=train_result.win_rate,
                    test_win_rate=test_result.win_rate,
                    efficiency_ratio=eff_ratio,
                    overfitting_flag=overfit
                )
                db.add(wf_window)
                await db.commit()

                window_summaries.append(WalkForwardWindowSummary(
                    window_index=window["window_index"],
                    train_period=f"{window['train_start'].strftime('%Y-%m')} -> {window['train_end'].strftime('%Y-%m')}",
                    test_period=f"{window['test_start'].strftime('%Y-%m')} -> {window['test_end'].strftime('%Y-%m')}",
                    train_pnl_r=train_result.total_pnl_r,
                    test_pnl_r=test_result.total_pnl_r,
                    efficiency_ratio=eff_ratio,
                    overfitting_flag=overfit
                ))

            # 3. Aggregate
            summary = self._aggregate_results(wf_experiment_id, window_summaries, config)
            return summary

    def _generate_windows(self, config: WalkForwardConfig) -> List[Dict]:
        windows = []
        current_start = config.total_start

        while True:
            train_end = current_start + relativedelta(months=config.train_months)
            test_end = train_end + relativedelta(months=config.test_months)

            if test_end > config.total_end:
                break

            windows.append({
                "window_index": len(windows) + 1,
                "train_start": current_start,
                "train_end": train_end,
                "test_start": train_end,
                "test_end": test_end
            })
            current_start += relativedelta(months=config.step_months)

        return windows

    def _aggregate_results(self, exp_id: UUID, windows: List[WalkForwardWindowSummary], config: WalkForwardConfig) -> WalkForwardResult:
        total = len(windows)
        avg_train = sum(w.train_pnl_r for w in windows) / total
        avg_test = sum(w.test_pnl_r for w in windows) / total
        avg_eff = sum(w.efficiency_ratio for w in windows) / total
        overfit_count = sum(1 for w in windows if w.overfitting_flag)
        pct_overfit = Decimal(str(overfit_count / total))

        profitable_windows = sum(1 for w in windows if w.test_pnl_r > 0)
        losing_windows = sum(1 for w in windows if w.test_pnl_r < 0)
        avg_out_pnl_r = sum(w.test_pnl_r for w in windows) / total

        # Revised Verdict Logic:
        # is_robust = True if (profitable windows >= losing) AND (avg out-sample > 0)
        is_robust = (profitable_windows >= losing_windows) and (avg_out_pnl_r > 0)

        # Verdict logic (Human readable text)
        if is_robust:
            if pct_overfit <= Decimal("0.20"):
                verdict = "✅ HIGHLY ROBUST — Excellent stability across regimes."
            elif profitable_windows > losing_windows * 1.5:
                verdict = "✅ ROBUST — Strong edge in out-sample testing."
            else:
                verdict = "⚠️ MODERATELY ROBUST — Stable but consider cautious scaling."
        else:
            verdict = "❌ NOT ROBUST — Edge does not generalize well to unseen data."

        return WalkForwardResult(
            wf_experiment_id=exp_id,
            total_windows=total,
            windows=windows,
            avg_train_pnl_r=avg_train,
            avg_test_pnl_r=avg_test,
            avg_efficiency_ratio=avg_eff,
            pct_overfitting_windows=pct_overfit,
            profitable_windows=profitable_windows,
            losing_windows=losing_windows,
            avg_out_pnl_r=avg_out_pnl_r,
            is_robust=is_robust,
            verdict=verdict
        )

    def print_report(self, result: WalkForwardResult, symbol_name: str):
        print("\n" + "═" * 70)
        print(f"WALK-FORWARD VALIDATION — {symbol_name}")
        print(f"Experiment ID: {result.wf_experiment_id}")
        print(f"Total Windows: {result.total_windows}")
        print("═" * 70)
        print(f"{'W':<3} {'Train Period':<20} {'Test Period':<20} {'In-R':<8} {'Out-R':<8} {'Eff.R':<7} {'Flag'}")
        print("─" * 70)
        for w in result.windows:
            flag = "✅" if not w.overfitting_flag else "⚠️"
            print(f"W{w.window_index:<2} {w.train_period:<20} {w.test_period:<20} {w.train_pnl_r:>+7.1f}R {w.test_pnl_r:>+7.1f}R {w.efficiency_ratio:>7.2f}  {flag}")
        print("─" * 70)
        print(f"Avg Efficiency:  {result.avg_efficiency_ratio:.2f}")
        print(f"Avg Out-PnL (R): {result.avg_out_pnl_r:+.2f}R")
        print(f"Windows:         {result.profitable_windows} Profitable / {result.losing_windows} Losing")
        print(f"Overfit Windows: {int(result.pct_overfitting_windows * result.total_windows)}/{result.total_windows} ({result.pct_overfitting_windows*100:.0f}%)")
        print("═" * 70)
        print(f"VERDICT: {result.verdict}")
        print("═" * 70 + "\n")
