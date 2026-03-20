import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

# Thêm 'backend' vào sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
backend_dir = os.path.join(root, 'backend')
sys.path.insert(0, backend_dir)

from app.database import Base
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig, SymbolExchangeConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///e:/Agent_AI_Antigravity/CBX_StrategyV1/test.db"

async def sync_v4():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Standard IDs
        SYMBOLS = {
            'BTCUSDC': UUID('bd1d0c1d-8564-40cb-a6d0-89376ebfa96a'),
            'BNBUSDC': UUID('bd2d0c2d-8564-40cb-a6d0-89376ebfa96b'),
            'SOLUSDC': UUID('bd3d0c3d-8564-40cb-a6d0-89376ebfa96c')
        }

        # 2. Deactivate old configs
        from sqlalchemy import update, delete
        await session.execute(delete(SymbolExchangeConfig))
        await session.execute(update(SymbolStrategyConfig).values(is_current=False))

        # 3. Insert/Sync V4
        for sym, sid in SYMBOLS.items():
            print(f"Syncing {sym}...")
            
            # Exchange Config
            if sym == 'BTCUSDC':
                tick = Decimal("0.1")
                lot = Decimal("0.001")
                min_qty = Decimal("0.001")
                notional = Decimal("5")
            elif sym == 'BNBUSDC':
                tick = Decimal("0.01")
                lot = Decimal("0.01")
                min_qty = Decimal("0.01")
                notional = Decimal("5")
            else: # SOL
                tick = Decimal("0.01")
                lot = Decimal("0.1")
                min_qty = Decimal("0.1")
                notional = Decimal("5")

            ex_cfg = SymbolExchangeConfig(
                config_id=uuid4(),
                symbol_id=sid,
                lot_size_step=lot,
                min_qty=min_qty,
                min_notional=notional,
                price_tick_size=tick,
                maker_fee_pct=Decimal("0.0002"),
                taker_fee_pct=Decimal("0.0005"),
                default_leverage=10,
                max_leverage=50,
                margin_type="ISOLATED",
                source="MANUAL_SYNC"
            )
            session.add(ex_cfg)

            v4 = SymbolStrategyConfig(
                strategy_config_id=uuid4(),
                symbol_id=sid,
                name=f"{sym} V4 Optimized",
                version=4,
                is_current=True,
                created_by="RESEARCHER",
                atr_period=14,
                atr_percentile_window=120,
                atr_percentile_threshold=Decimal("20.0"),
                range_bars=12,
                range_percentile_threshold=Decimal("20.0"),
                bb_period=20,
                bb_std=Decimal("2.0"),
                bb_width_percentile_threshold=Decimal("20.0"),
                volume_percentile_threshold=Decimal("60.0"),
                compression_min_bars=8,
                compression_max_bars=24,
                min_conditions_met=3,
                breakout_distance_min_atr=Decimal("0.20"),
                breakout_body_ratio_min=Decimal("0.50"),
                breakout_close_position_long=Decimal("0.65"),
                breakout_close_position_short=Decimal("0.35"),
                breakout_volume_ratio_min=Decimal("1.10"),
                breakout_volume_percentile_min=Decimal("60.0"),
                breakout_bar_size_max_atr=Decimal("2.50"),
                false_break_limit=2,
                expansion_lookforward_bars=3,
                expansion_body_loss_max_pct=Decimal("50.0"),
                retest_max_bars=3,
                stop_loss_atr_buffer=Decimal("0.20"),
                entry_retest_buffer_atr=Decimal("0.10") if sym == 'SOLUSDC' else Decimal("0.05"),
                partial_exit_r_level=Decimal("0.80"),
                partial_exit_pct=Decimal("0.30"),
                time_stop_bars=30,
                ema_period_context=50,
                context_timeframe="1h",
                execution_timeframe="15m",
                risk_per_trade_pct=Decimal("0.25"), # 0.25% (engine will divide by 100)
                max_position_per_symbol=1
            )
            session.add(v4)
        
        await session.commit()
    print("V4 and Exchange Config Sync Done (CORRECTED VALUES).")

if __name__ == "__main__":
    asyncio.run(sync_v4())
