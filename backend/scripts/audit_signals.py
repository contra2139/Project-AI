import os
import sys
import asyncio
import pandas as pd
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.strategy.feature_engine import FeatureEngine
from app.strategy.compression_detector import CompressionDetector
from app.strategy.breakout_detector import BreakoutDetector
from app.strategy.context_filter import ContextFilter
from app.strategy.expansion_validator import ExpansionValidator
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig

db_path = 'test.db'
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.abspath(db_path)}"
engine_sa = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine_sa, class_=AsyncSession, expire_on_commit=False)

async def audit_full_year():
    print("="*50)
    print("CBX - FULL YEAR SIGNAL AUDIT (SCIENTIFIC)")
    print("="*50)
    
    async with AsyncSessionLocal() as session:
        # 1. Load Data
        print("Loading 1 year of data for BTCUSDC...")
        sym_id = (await session.execute(select(SymbolRegistry.symbol_id).where(SymbolRegistry.symbol == 'BTCUSDC'))).scalar()
        stmt = select(SymbolStrategyConfig).where(SymbolStrategyConfig.symbol_id == sym_id, SymbolStrategyConfig.is_current == True)
        strat = (await session.execute(stmt)).scalar_one()
        params = {c.name: getattr(strat, c.name) for c in strat.__table__.columns}
        
        query = text("SELECT timestamp, open, high, low, close, volume FROM ohlcv_15m WHERE symbol='BTCUSDC' ORDER BY timestamp")
        df = pd.DataFrame((await session.execute(query)).fetchall())
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        query_1h = text("SELECT timestamp, open, high, low, close, volume FROM ohlcv_1h WHERE symbol='BTCUSDC' ORDER BY timestamp")
        df_1h = pd.DataFrame((await session.execute(query_1h)).fetchall())
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
        
        # 2. Features
        print("Computing features...")
        fe = FeatureEngine()
        df = fe.compute_features(df)
        df = fe.calculate_percentiles(df)
        
        # ALSO compute features for 1H data (needed for EMA50 context)
        df_1h = fe.compute_features(df_1h, atr_period=14)
        
        # 3. Detect
        print(f"Scanning {len(df)} bars with V2 params...")
        cd = CompressionDetector()
        bd = BreakoutDetector()
        cf = ContextFilter()
        ev = ExpansionValidator()
        
        stats = {
            "Total Bars": len(df),
            "Compression Zones": 0,
            "Potential Breakouts": 0,
            "Valid Breakouts (BD)": 0,
            "Allowed by Context (CF)": 0,
            "Confirmed by Expansion (EV)": 0,
            "BD_Failures": {},
            "CF_Failures": 0,
            "EV_Failures": 0
        }
        
        warmup = 120
        for i in range(warmup, len(df)):
            current_bar = df.iloc[i]
            slice_df = df.iloc[max(0, i-30):i] # EXCLUDE current bar
            
            zone = cd.detect(slice_df, None, sym_id, params)
            if not zone: continue
            stats["Compression Zones"] += 1
            
            res_bd = bd.detect(current_bar, zone, current_bar, params)
            
            # DEBUG TOP 10 ZONES
            if stats["Compression Zones"] <= 10:
                print(f"DEBUG Zone {stats['Compression Zones']} at {current_bar['timestamp']}:")
                print(f"  Close: {current_bar['close']:.2f}, Zone High: {zone.high:.2f}, Zone Low: {zone.low:.2f}")
                print(f"  BD Result: {res_bd.is_valid}, Reasons: {res_bd.invalid_reasons}")
                if res_bd.side:
                    print(f"  Side: {res_bd.side}, Distance: {res_bd.breakout_distance_atr:.2f}, Body: {res_bd.body_to_range:.2f}")

            if not res_bd.is_valid:
                for reason in res_bd.invalid_reasons:
                    stats["BD_Failures"][reason] = stats["BD_Failures"].get(reason, 0) + 1
                continue
            
            stats["Valid Breakouts (BD)"] += 1
            
            # Context
            h1_data = df_1h[df_1h.timestamp <= current_bar['timestamp']].iloc[-10:]
            if h1_data.empty: continue
            res_cf = cf.check(h1_data, res_bd.side, res_bd, params)
            if not res_cf.allowed:
                stats["CF_Failures"] += 1
                continue
            
            stats["Allowed by Context (CF)"] += 1
            
            # Expansion
            next_bars = df.iloc[i+1 : i+4].to_dict('records')
            res_ev = ev.validate(res_bd, next_bars, zone, params)
            if not res_ev.is_confirmed:
                stats["EV_Failures"] += 1
                continue
                
            stats["Confirmed by Expansion (EV)"] += 1
            
        print("\n" + "="*50)
        print("AUDIT RESULTS:")
        for k, v in stats.items():
            if k == "BD_Failures":
                print(f"\n{k}:")
                for r, c in v.items():
                    print(f"  - {r}: {c}")
            else:
                print(f"{k}: {v}")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(audit_full_year())
