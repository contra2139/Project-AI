import asyncio
import os
import sys
import logging
import csv
print(f"SCRIPT PATH: {os.path.abspath(__file__)}")
sys.stdout.flush()
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from typing import List, Any
import pandas as pd
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backtest.engine import BacktestEngine, BacktestConfig
from app.backtest.reporter import BacktestReporter
from app.backtest.walk_forward import WalkForwardValidator, WalkForwardConfig
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig
from app.models.trade import Trade
from app.database import Base

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Database Setup (Prefer environment variable)
env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    DATABASE_URL = env_db_url
    print(f" Using Database from ENV: {DATABASE_URL}")
else:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'test.db'))
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
    print(f" Using Default Database: {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"timeout": 60})
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SYMBOLS = ["BTCUSDC", "BNBUSDC", "SOLUSDC"]
RESULTS_DIR = os.path.abspath(os.path.join(os.getcwd(), "backtest_results_v7"))
print(f"DEBUG: RESULTS_DIR = {RESULTS_DIR}")
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

with open("FINAL_CONFIRMATION_V7.txt", "w") as f:
    f.write(f"V7 Backtest ran at {datetime.now()}\n")
    f.write(f"RESULTS_DIR = {RESULTS_DIR}\n")

async def get_symbol_ids(session: AsyncSession):
    """Retrieve symbol_id and strategy_config_id for the symbols."""
    mapping = {}
    print(f"DEBUG: Entering get_symbol_ids. SYMBOLS={SYMBOLS}", file=sys.stderr)
    for sym_name in SYMBOLS:
        print(f" Looking up {sym_name}...", file=sys.stderr)
        try:
            stmt = select(SymbolRegistry.symbol_id).where(SymbolRegistry.symbol == sym_name)
            res = await session.execute(stmt)
            symbol_id = res.scalar_one_or_none()
            
            if symbol_id:
                print(f"  - Found Symbol ID: {symbol_id} (Type: {type(symbol_id)})", file=sys.stderr)
                stmt_strat = select(SymbolStrategyConfig.strategy_config_id).join(
                    SymbolRegistry, SymbolStrategyConfig.symbol_id == SymbolRegistry.symbol_id
                ).where(
                    SymbolRegistry.symbol == sym_name,
                    SymbolStrategyConfig.is_current == True
                ).order_by(SymbolStrategyConfig.created_at.desc())
                res_strat = await session.execute(stmt_strat)
                strat_id = res_strat.scalar()
                if strat_id:
                    print(f"  - Found Strategy ID: {strat_id}", file=sys.stderr)
                    mapping[sym_name] = {"symbol_id": symbol_id, "strat_id": strat_id}
                else:
                    print(f"  -  NO STRATEGY CONFIG FOUND for {sym_name}!", file=sys.stderr)
            else:
                print(f"  -  SYMBOL NOT FOUND in registry!", file=sys.stderr)
                logger.warning(f"Symbol {sym_name} not found in registry.")
        except Exception as e:
            print(f"  -  ERROR during lookup for {sym_name}: {e}", file=sys.stderr)
        sys.stderr.flush()
    return mapping

async def save_trades_to_csv(trades: List[Trade], symbol: str):
    """Save trade objects to CSV directly."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filename = os.path.join(RESULTS_DIR, f"{symbol}_trades.csv")
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['trade_id', 'entry_time', 'exit_time', 'side', 'entry_price', 'exit_price', 'total_pnl_r', 'total_pnl_usd', 'exit_model']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for t in trades:
            writer.writerow({
                'trade_id': str(t.trade_id),
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'side': t.side,
                'entry_price': float(t.entry_price or 0),
                'exit_price': float(t.avg_exit_price or 0),
                'total_pnl_r': float(t.total_pnl_r or 0),
                'total_pnl_usd': float(t.total_pnl_usd or 0),
                'exit_model': t.exit_model
            })

async def run_symbol_backtest(sym_name, ids, session_factory):
    """Execute backtest and walk-forward for a single symbol."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 1. Backtest Engine Run
    engine = BacktestEngine(session_factory)
    
    config = BacktestConfig(
        symbol_id=ids["symbol_id"],
        strategy_config_id=ids["strat_id"],
        initial_equity=Decimal("10000"),
        data_start=datetime(2024, 1, 1),
        data_end=datetime(2026, 2, 28),
        entry_model="FOLLOW_THROUGH",
        side_filter="BOTH"
    )
    
    print(f"DEBUG: [{sym_name}] Starting backtest run (2024-2026)...")
    result = await engine.run(config)
    run_id = result.run_id
    print(f"DEBUG: [{sym_name}] Backtest engine finished. run_id={run_id}")
    
    # 2. Report Generation
    reporter = BacktestReporter(session_factory)
    summary = await reporter.generate_summary(run_id)
    summary.symbol = sym_name 
    
    # Custom side breakdown for V7
    async with session_factory() as db:
        res_side = await db.execute(text("""
            SELECT side, COUNT(*), 
                   SUM(CASE WHEN total_pnl_r > 0 THEN 1 ELSE 0 END) as wins,
                   AVG(CAST(total_pnl_r AS FLOAT)) as avg_r
            FROM trade WHERE run_id = :rid GROUP BY side
        """), {"rid": str(run_id)})
        side_stats = res_side.fetchall()

    report_file = os.path.join(RESULTS_DIR, f"{sym_name}_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        import io
        from contextlib import redirect_stdout
        captured = io.StringIO()
        with redirect_stdout(captured):
            reporter.print_report(summary)
            print("\n--- Long/Short Breakdown ---")
            for row in side_stats:
                print(f"Side: {row[0]:>5} | Count: {row[1]:>3} | Wins: {row[2]:>3} | Avg R: {row[3]:>6.2f}")
        f.write(captured.getvalue())
    
    # Also print to terminal
    print(f"\n===== {sym_name} REPORT =====")
    print(captured.getvalue())
    
    # 3. Save Trades to CSV
    await save_trades_to_csv(result.trades, sym_name)
    
    # 4. Walk-Forward Validation
    wf_config = WalkForwardConfig(
        symbol_id=ids["symbol_id"],
        strategy_config_id=ids["strat_id"],
        total_start=datetime(2024, 1, 1),
        total_end=datetime(2026, 2, 28),
        train_months=6,
        test_months=2,
        step_months=1,
        initial_equity=Decimal("10000")
    )
    
    logger.info(f"Running Walk-Forward Validation for {sym_name} (Train=6m, Test=2m)...")
    validator = WalkForwardValidator(session_factory)
    wf_result = await validator.run(wf_config)
    
    # Save WF Summary
    wf_file = os.path.join(RESULTS_DIR, "walkforward_v7_revised.txt")
    with open(wf_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"WALK-FORWARD SUMMARY: {sym_name}\n")
        f.write(f"{'='*50}\n")
        import io
        from contextlib import redirect_stdout
        captured = io.StringIO()
        with redirect_stdout(captured):
            validator.print_report(wf_result, sym_name)
        f.write(captured.getvalue())
    
    return summary

async def main():
    logger.info("Starting Comprehensive Backtest Suite Strategy V7 (2024-2026)...")
    
    async with AsyncSessionLocal() as session:
        mapping = await get_symbol_ids(session)
    
    if not mapping:
        logger.error("No symbols found. Mapping is empty.")
        return

    # SEQUENTIAL EXECUTION to avoid SQLite "database is locked" errors
    for sym_name, ids in mapping.items():
        try:
            await run_symbol_backtest(sym_name, ids, AsyncSessionLocal)
        except Exception as e:
            logger.error(f"Error during backtest for {sym_name}:")
            import traceback
            traceback.print_exc()

    logger.info("\n" + "="*50)
    logger.info("BACKTESTING V7 COMPLETE!")
    logger.info(f"All reports saved to: {os.path.abspath(RESULTS_DIR)}")
    logger.info("="*50)

if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except Exception as e:
        print(f" FATAL ERROR IN SCRIPT: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)
