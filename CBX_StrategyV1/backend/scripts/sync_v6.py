import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

# Add backend to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
backend_dir = os.path.join(root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import AsyncSessionLocal
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig, SymbolExchangeConfig
from sqlalchemy import select, update

async def sync_v6():
    print("=== Strategy V6 Sync Starting ===")
    
    symbols = ["BTCUSDC", "BNBUSDC", "SOLUSDC"]
    
    async with AsyncSessionLocal() as session:
        for sym in symbols:
            # 1. Get symbol ID
            res = await session.execute(select(SymbolRegistry).where(SymbolRegistry.symbol == sym))
            symbol = res.scalar_one_or_none()
            if not symbol:
                print(f"Symbol {sym} not found. Skipping.")
                continue
            
            symbol_id = symbol.symbol_id
            print(f"Processing {sym} ({symbol_id})...")
            
            # 2. Deactivate all existing configs for this symbol
            await session.execute(
                update(SymbolStrategyConfig)
                .where(SymbolStrategyConfig.symbol_id == symbol_id)
                .values(is_current=False)
            )
            print(f"  Deactivated all previous configs for {sym}.")
            
            # 3. Insert V6
            # Use V4 Exit logic, modified Entry logic
            v6_config = SymbolStrategyConfig(
                strategy_config_id=uuid4(),
                symbol_id=symbol_id,
                version=6,
                is_current=True,
                created_by="Antigravity",
                
                # Nới lỏng ENTRY (Point 1 from user)
                atr_percentile_threshold=30.0,
                range_percentile_threshold=30.0,
                bb_width_percentile_threshold=30.0,
                volume_percentile_threshold=70.0,
                compression_min_bars=8,
                min_conditions_met=2,
                
                # BREAKOUT parameters (Hold from V4)
                breakout_distance_min_atr=Decimal("0.20"),
                breakout_body_ratio_min=Decimal("0.50"),
                breakout_volume_ratio_min=Decimal("1.10"),
                breakout_bar_size_max_atr=Decimal("2.50"),
                
                # EXIT params (Hold from V4)
                time_stop_bars=30,
                partial_exit_r_level=Decimal("0.80"),
                partial_exit_pct=Decimal("0.30"),
                stop_loss_atr_buffer=Decimal("0.20"),
                
                # Standard params
                atr_period=14,
                compression_max_bars=24,
                breakout_close_position_long=Decimal("0.65"),
                breakout_close_position_short=Decimal("0.35")
            )
            session.add(v6_config)
            print(f"  Added Version 6 for {sym}.")
            
        await session.commit()
        print("=== Database Committed ===")
        
        # 4. Verify (Point 3 from user)
        for sym in symbols:
            res = await session.execute(select(SymbolRegistry).where(SymbolRegistry.symbol == sym))
            s = res.scalar()
            res_active = await session.execute(
                select(SymbolStrategyConfig)
                .where(SymbolStrategyConfig.symbol_id == s.symbol_id, SymbolStrategyConfig.is_current == True)
            )
            active_configs = res_active.scalars().all()
            print(f"Verification {sym}: Count of is_current=1: {len(active_configs)}")
            if len(active_configs) != 1:
                print(f"  WARNING: {sym} has {len(active_configs)} active configs!")

if __name__ == "__main__":
    asyncio.run(sync_v6())
