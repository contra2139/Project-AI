import asyncio
import os
import sys
import logging
from datetime import datetime
from decimal import Decimal

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backtest.engine import BacktestEngine, BacktestConfig
from app.database import AsyncSessionLocal

async def run_single():
    # Setup
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test.db"))
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
    
    engine = BacktestEngine(AsyncSessionLocal)
    
    from sqlalchemy import select
    from app.models.symbol import SymbolRegistry, SymbolStrategyConfig
    
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(SymbolRegistry).where(SymbolRegistry.symbol == 'BTCUSDC'))
        sym = res.scalar_one()
        res = await db.execute(select(SymbolStrategyConfig).where(SymbolStrategyConfig.symbol_id == sym.symbol_id, SymbolStrategyConfig.is_current == 1))
        strat = res.scalar_one()
        
        config = BacktestConfig(
            symbol_id=sym.symbol_id,
            strategy_config_id=strat.strategy_config_id,
            data_start=datetime(2024, 3, 1),
            data_end=datetime(2025, 3, 1),
            run_name="Single Run BTC"
        )
        
        print(f"Starting isolated BTC backtest from {DB_PATH}...")
        try:
            result = await engine.run(config)
            print(f"DONE! Total Trades: {result.total_trades}, PnL: {result.total_pnl_r}R")
        except Exception as e:
            import traceback
            print(f"FATAL ERROR: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_single())
