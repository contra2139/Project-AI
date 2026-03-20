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

async def sync_v7():
    print("=== Strategy V7 Sync Starting ===")
    
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
            
            # 3. Insert V7
            v7_config = SymbolStrategyConfig(
                strategy_config_id=uuid4(),
                symbol_id=symbol_id,
                version=7,
                is_current=True,
                created_by="Antigravity",
                
                # COMPRESSION (Keep V6)
                atr_percentile_threshold=Decimal("30.0"),
                range_percentile_threshold=Decimal("30.0"),
                bb_width_percentile_threshold=Decimal("30.0"),
                volume_percentile_threshold=Decimal("70.0"),
                compression_min_bars=8,
                compression_max_bars=24,
                min_conditions_met=2,
                
                # BREAKOUT (Tighten quality)
                breakout_distance_min_atr=Decimal("0.25"),
                breakout_body_ratio_min=Decimal("0.55"),
                breakout_close_position_long=Decimal("0.70"),
                breakout_close_position_short=Decimal("0.30"),
                breakout_volume_ratio_min=Decimal("1.20"),
                breakout_volume_percentile_min=Decimal("65.0"),
                breakout_bar_size_max_atr=Decimal("2.50"),
                
                # NEW V7 CONTEXT FILTER
                ema_period_context=50,
                context_timeframe="1h",
                long_min_ema_slope=Decimal("0.0003"),
                long_min_price_vs_ema=Decimal("0.005"),
                short_max_ema_slope=Decimal("-0.0003"),
                short_max_price_vs_ema=Decimal("-0.005"),
                
                # EXIT (V6 Exit, but new Trailing Multiplier)
                stop_loss_atr_buffer=Decimal("0.20"),
                partial_exit_r_level=Decimal("0.80"),
                partial_exit_pct=Decimal("0.30"),
                time_stop_bars=30,
                trailing_atr_multiplier=Decimal("2.50"),
                
                # Standard params
                atr_period=14,
                risk_per_trade_pct=Decimal("0.0025"),
                max_position_per_symbol=1,
                execution_timeframe="15m"
            )
            session.add(v7_config)
            print(f"  Added Version 7 for {sym}.")
            
        await session.commit()
        print("=== Database Committed ===")
        
        # 4. Verify
        res_active = await session.execute(
            select(SymbolStrategyConfig)
            .where(SymbolStrategyConfig.is_current == True)
        )
        active_configs = res_active.scalars().all()
        print(f"Total active configs: {len(active_configs)}")

if __name__ == "__main__":
    asyncio.run(sync_v7())
