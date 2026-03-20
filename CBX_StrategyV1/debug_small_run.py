import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime
from uuid import UUID

# Add backend to path
sys.path.insert(0, os.path.abspath("backend"))

from app.backtest.engine import BacktestEngine, BacktestConfig
from app.database import AsyncSessionLocal
from app.models.symbol import SymbolStrategyConfig
from sqlalchemy import select

async def test_small_run():
    engine = BacktestEngine(AsyncSessionLocal)
    
    # BTC IDs
    btc_id = UUID('bd1d0c1d-8564-40cb-a6d0-89376ebfa96a')
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SymbolStrategyConfig.strategy_config_id).where(SymbolStrategyConfig.symbol_id == btc_id, SymbolStrategyConfig.is_current == True))
        strat_id = res.scalar()
        print(f"DEBUG: Found strat_id={strat_id} (type: {type(strat_id)})")
        
    if not strat_id:
        print("No strategy config found for BTC")
        return

    config = BacktestConfig(
        symbol_id=btc_id,
        strategy_config_id=strat_id,
        initial_equity=Decimal("100000"),
        data_start=datetime(2024, 3, 1),
        data_end=datetime(2024, 3, 5), # ONLY 4 DAYS
        run_name="Debug Root Run"
    )
    
    print(f"Starting Small Backtest (4 days) for {btc_id}...")
    result = await engine.run(config)
    print(f"Finished! Trades: {result.total_trades}, PnL: {result.total_pnl_r}R")

if __name__ == "__main__":
    asyncio.run(test_small_run())
