import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import ResearchRun
from app.models.trade import Trade

logger = logging.getLogger(__name__)

@dataclass
class BacktestSummary:
    run_name: str
    symbol: str
    data_range: str
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: Decimal
    total_pnl_r: Decimal
    total_pnl_usd: Decimal
    profit_factor: Decimal
    max_drawdown_r: Decimal
    avg_win_r: Decimal
    avg_loss_r: Decimal
    avg_hold_bars: Decimal
    exit_breakdown: Dict[str, int]
    long_stats: Dict[str, Any]
    short_stats: Dict[str, Any]

class BacktestReporter:
    def __init__(self, db_factory):
        self.db_factory = db_factory

    async def generate_summary(self, run_id: UUID) -> BacktestSummary:
        async with self.db_factory() as db:
            from app.models.symbol import SymbolRegistry
            # Fetch Run and Symbol Name
            stmt_run = select(ResearchRun, SymbolRegistry.symbol).join(
                SymbolRegistry, ResearchRun.symbol_id == SymbolRegistry.symbol_id
            ).where(ResearchRun.run_id == run_id)
            res_run = await db.execute(stmt_run)
            row = res_run.one()
            run = row[0]
            symbol_name = row[1]
            
            # Fetch Trades
            stmt_trades = select(Trade).where(Trade.run_id == run_id)
            res_trades = await db.execute(stmt_trades)
            trades = res_trades.scalars().all()
            
            total = len(trades)
            wins = [t for t in trades if (t.total_pnl_r or 0) > 0]
            losses = [t for t in trades if (t.total_pnl_r or 0) <= 0]
            
            total_r = sum(t.total_pnl_r or 0 for t in trades)
            total_usd = sum(t.total_pnl_usd or 0 for t in trades)

            # Sort trades by exit_time for chronological equity curve
            sorted_trades = sorted(trades, key=lambda x: x.exit_time if x.exit_time else x.entry_time)
            
            peak_r = Decimal("0")
            current_r = Decimal("0")
            max_dd_r = Decimal("0")
            
            for t in sorted_trades:
                current_r += (t.total_pnl_r or Decimal("0"))
                if current_r > peak_r:
                    peak_r = current_r
                dd = current_r - peak_r
                if dd < max_dd_r:
                    max_dd_r = dd

            # Profit Factor
            gross_win = sum(t.total_pnl_r or 0 for t in wins)
            gross_loss = abs(sum(t.total_pnl_r or 0 for t in losses))
            pf = gross_win / gross_loss if gross_loss > 0 else Decimal("0")
            
            # Exit breakdown
            exits = {}
            for t in trades:
                exits[t.exit_model] = exits.get(t.exit_model, 0) + 1
                
            return BacktestSummary(
                run_name=run.run_name,
                symbol=symbol_name,
                data_range=f"{run.data_start} -> {run.data_end}",
                total_trades=total,
                win_count=len(wins),
                loss_count=len(losses),
                win_rate=Decimal(str(len(wins)/total)) if total > 0 else Decimal("0"),
                total_pnl_r=Decimal(str(total_r)),
                total_pnl_usd=Decimal(str(total_usd)),
                profit_factor=Decimal(str(pf)),
                max_drawdown_r=max_dd_r,
                avg_win_r=Decimal(str(gross_win/len(wins))) if wins else Decimal("0"),
                avg_loss_r=Decimal(str(gross_loss/len(losses))) if losses else Decimal("0"),
                avg_hold_bars=Decimal("0"), # Placeholder
                exit_breakdown=exits,
                long_stats={},
                short_stats={}
            )

    def print_report(self, summary: BacktestSummary):
        print("="*40)
        print(f"CBX BACKTEST RESULTS - {summary.symbol}")
        print(f"Run: {summary.run_name}")
        print(f"Period: {summary.data_range}")
        print("="*40)
        print(f"Trades:    {summary.total_trades} ({summary.win_count}W / {summary.loss_count}L)")
        print(f"Win Rate:  {summary.win_rate:.1%}")
        print(f"Total PnL: {summary.total_pnl_r:+.2f}R  (${summary.total_pnl_usd:+.0f})")
        print(f"Max DD:    {summary.max_drawdown_r:.2f}R")
        print(f"PF:        {summary.profit_factor:.2f}")
        print("-"*20)
        print("Exit breakdown:")
        for reason, count in summary.exit_breakdown.items():
            pct = count / summary.total_trades if summary.total_trades > 0 else 0
            print(f"{reason:15}: {count} ({pct:.0%})")
        print("="*40)
