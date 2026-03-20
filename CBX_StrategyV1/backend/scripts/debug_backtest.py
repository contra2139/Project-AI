import os
import sys
import asyncio
import uuid
import pandas as pd
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.strategy.feature_engine import FeatureEngine
from app.strategy.compression_detector import CompressionDetector
from app.backtest.engine import BacktestEngine, BacktestConfig
from app.models.symbol import SymbolRegistry, SymbolStrategyConfig
from app.database import Base

load_dotenv()
load_dotenv('backend/.env')

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'test.db'))
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

print(f"DEBUG: Using Database {DATABASE_URL}")
print(f"DEBUG: SymbolStrategyConfig has max_position_per_symbol: {hasattr(SymbolStrategyConfig, 'max_position_per_symbol')}")
print(f"DEBUG: SymbolStrategyConfig has max_positions_per_symbol: {hasattr(SymbolStrategyConfig, 'max_positions_per_symbol')}")

engine_sa = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine_sa, class_=AsyncSession, expire_on_commit=False)

async def debug_backtest():
    print("="*50, file=sys.stderr)
    print("CBX STRATEGY - ZERO TRADES DIAGNOSIS", file=sys.stderr)
    print("="*50, file=sys.stderr)
    
    async with engine_sa.connect() as conn:
        print("DEBUG: Checking table_info at runtime...", file=sys.stderr)
        res = await conn.execute(text("PRAGMA table_info(symbol_strategy_config)"))
        cols = res.fetchall()
        for c in cols:
            print(f"  Col: {c[1]}", file=sys.stderr)
        sys.stderr.flush()

    results = {"Layer 1": "PENDING", "Layer 2": "PENDING", "Layer 3": "PENDING", "Layer 4": "PENDING", "Layer 5": "PENDING"}
    root_cause = "Unknown"

    async with AsyncSessionLocal() as session:
        # Layer 1 - Check data in DB
        print("\n[LAYER 1] Checking data in DB...")
        try:
            # Check BTCUSDC 15m
            query_count = text("SELECT COUNT(*) FROM ohlcv_15m WHERE symbol='BTCUSDC'")
            query_range = text("SELECT MIN(timestamp), MAX(timestamp) FROM ohlcv_15m WHERE symbol='BTCUSDC'")
            
            cnt = (await session.execute(query_count)).scalar()
            times = (await session.execute(query_range)).fetchone()
            
            if cnt > 0:
                # Robust date parsing
                t_start = times[0]
                t_end = times[1]
                if isinstance(t_start, str):
                    try:
                        t_start = datetime.fromisoformat(t_start.replace('Z', '+00:00'))
                    except:
                        t_start = datetime.strptime(t_start.split('.')[0], '%Y-%m-%d %H:%M:%S')
                if isinstance(t_end, str):
                    try:
                        t_end = datetime.fromisoformat(t_end.replace('Z', '+00:00'))
                    except:
                        t_end = datetime.strptime(t_end.split('.')[0], '%Y-%m-%d %H:%M:%S')

                print(f" BTCUSDC 15m: {cnt} rows, t {t_start} n {t_end}")
                results["Layer 1"] = "OK"
                # Store for later
                global_start = t_start
                global_end = t_end
            else:
                print(" LI: Khng c data, fetch_ohlcv.py cha chy ng")
                results["Layer 1"] = "FAIL"
                root_cause = "No OHLCV data in database"
                return print_summary(results, root_cause)
        except Exception as e:
            print(f" LI Tng 1: {e}")
            results["Layer 1"] = "FAIL"
            root_cause = f"DB Error: {e}"
            return print_summary(results, root_cause)

        # TNG 2  Kim tra Feature Engine
        print("\n[TNG 2] Kim tra Feature Engine...")
        try:
            query_data = text("SELECT * FROM ohlcv_15m WHERE symbol='BTCUSDC' ORDER BY timestamp LIMIT 200")
            rows = (await session.execute(query_data)).fetchall()
            df = pd.DataFrame(rows)
            
            fe = FeatureEngine()
            df_feat = fe.compute_features(df.copy(), atr_period=14)
            
            cols = ['timestamp', 'close', 'atr_norm']
            available_cols = [c for c in cols if c in df_feat.columns]
            print(df_feat[available_cols].tail(5))
            
            if df_feat['atr_norm'].isnull().all():
                print(" LI: Feature Engine khng tnh c (NaN)")
                results["Layer 2"] = "FAIL"
                root_cause = "Feature Engine returning NaN"
            else:
                print(" Feature Engine: OK")
                results["Layer 2"] = "OK"
        except Exception as e:
            print(f" LI Tng 2: {e}")
            results["Layer 2"] = "FAIL"
            root_cause = f"Feature Error: {e}"

        if results["Layer 2"] == "FAIL": return print_summary(results, root_cause)

        # TNG 3  Kim tra Percentile Engine
        print("\n[TNG 3] Kim tra Percentile Engine...")
        try:
            df_perc = fe.calculate_percentiles(df_feat.copy(), window=120)
            
            p_cols = ['atr_norm_pct', 'range_pct_pct', 'bb_width_pct', 'vol_ratio_pct']
            print("5 bars cui:")
            print(df_perc[p_cols].tail(5))
            
            total = len(df_perc)
            low_atr = len(df_perc[df_perc['atr_norm_pct'] <= 20])
            pct_low = (low_atr / total) * 100 if total > 0 else 0
            
            print(f"Bao nhiu bars di ngng 20%? {low_atr}/{total} ({pct_low:.1f}%)")
            results["Layer 3"] = "OK"
        except Exception as e:
            print(f" LI Tng 3: {e}")
            results["Layer 3"] = "FAIL"
            root_cause = f"Percentile Error: {e}"

        if results["Layer 3"] == "FAIL": return print_summary(results, root_cause)

        # TNG 4  Kim tra Compression Detector
        print("\n[TNG 4] Kim tra Compression Detector...")
        try:
            # Fetch IDs and params early
            sym_id = (await session.execute(select(SymbolRegistry.symbol_id).where(SymbolRegistry.symbol == 'BTCUSDC'))).scalar()
            stmt = select(SymbolStrategyConfig).join(SymbolRegistry).where(SymbolRegistry.symbol == 'BTCUSDC', SymbolStrategyConfig.is_current == True)
            strat = (await session.execute(stmt)).scalar_one()
            params = {c.name: getattr(strat, c.name) for c in strat.__table__.columns}

            detector = CompressionDetector()
            
            # Trace last bar
            last_bar = df_perc.iloc[-1]
            atr_p = float(last_bar.get('atr_norm_pct', 100))
            rng_p = float(last_bar.get('range_pct_pct', 100))
            bbw_p = float(last_bar.get('bb_width_pct', 100))
            vol_p = float(last_bar.get('vol_ratio_pct', 100))
            
            atr_t = float(params.get('atr_percentile_threshold', 20))
            rng_t = float(params.get('range_percentile_threshold', 20))
            bbw_t = float(params.get('bb_width_percentile_threshold', 20))
            vol_t = float(params.get('volume_percentile_threshold', 60))
            min_c = int(params.get('min_conditions_met', 3))
            
            met = 0
            print(f"Bar cui ({last_bar['timestamp']}):")
            print(f"  atr_p: {atr_p:.1f} (t={atr_t}) -> {'PASS' if atr_p <= atr_t else 'FAIL'}")
            if atr_p <= atr_t: met += 1
            print(f"  rng_p: {rng_p:.1f} (t={rng_t}) -> {'PASS' if rng_p <= rng_t else 'FAIL'}")
            if rng_p <= rng_t: met += 1
            print(f"  bbw_p: {bbw_p:.1f} (t={bbw_t}) -> {'PASS' if bbw_p <= bbw_t else 'FAIL'}")
            if bbw_p <= bbw_t: met += 1
            print(f"  vol_p: {vol_p:.1f} (t={vol_t}) -> {'PASS' if vol_p <= vol_t else 'FAIL'}")
            if vol_p <= vol_t: met += 1
            print(f"  Conditions met: {met} (cn >= {min_c})")
            
            # Run detector on all 200 bars
            zones = []
            test_run_id = uuid.uuid4()
            # Simulation-like detection
            for i in range(20, len(df_perc)):
                slice_df = df_perc.iloc[max(0, i-30):i+1]
                zone = detector.detect(slice_df, test_run_id, sym_id, params)
                if zone: zones.append((i, zone))
            
            print(f"Tm thy {len(zones)} compression zones trong 200 bars u")
            results["Layer 4"] = "OK"
        except Exception as e:
            print(f" LI Tng 4: {e}")
            results["Layer 4"] = "FAIL"
            root_cause = f"Detector Error: {e}"

        if results["Layer 4"] == "FAIL": return print_summary(results, root_cause)

        # TNG 5  Kim tra BacktestEngine data loading
        print("\n[TNG 5] Kim tra BacktestEngine data loading...")
        try:
            bt_engine = BacktestEngine(AsyncSessionLocal)
            # Find symbol_id
            sym_id = (await session.execute(select(SymbolRegistry.symbol_id).where(SymbolRegistry.symbol == 'BTCUSDC'))).scalar()
            strat_id = (await session.execute(select(SymbolStrategyConfig.strategy_config_id).where(SymbolStrategyConfig.symbol_id == sym_id, SymbolStrategyConfig.is_current == True))).scalar()
            
            config = BacktestConfig(
                symbol_id=sym_id,
                strategy_config_id=strat_id,
                data_start=global_start,
                data_end=global_end
            )
            
            df_15m, df_1h, _, _ = await bt_engine._load_data(session, config)
            print(f"Engine loaded {len(df_15m)} bars cho 15m, {len(df_1h)} bars cho 1h")
            
            if len(df_15m) == 0:
                print(" LI: Engine khng load c data t DB")
                results["Layer 5"] = "FAIL"
                root_cause = "Engine loaded 0 bars"
            else:
                results["Layer 5"] = "OK"
        except Exception as e:
            print(f" LI Tng 5: {e}")
            results["Layer 5"] = "FAIL"
            root_cause = f"Engine Load Error: {e}"

        if results["Layer 5"] == "FAIL": return print_summary(results, root_cause)

        # TNG 6  Kim tra Breakout Detector
        print("\n[TNG 6] Kim tra Breakout Detector...")
        try:
            from app.strategy.breakout_detector import BreakoutDetector
            bd = BreakoutDetector()
            breakouts = []
            
            # Use found zones from Layer 4 if any
            if zones:
                # For debug, we check the bars immediately following each zone
                for z_end, zone in zones[:5]: # Check first 5 zones
                    # Check next 3 bars for breakout
                    for j in range(z_end + 1, min(z_end + 4, len(df_perc))):
                        bar = df_perc.iloc[j]
                        res = bd.detect(bar, zone, bar, params)
                        if res.is_valid:
                            breakouts.append(res)
                            print(f" Breakout tm thy ti {bar['timestamp']} (Side: {res.side})")
                        else:
                            # Print why it failed for the first zone/bar combo
                            if len(breakouts) == 0 and j == z_end + 1:
                                print(f"  Bar {bar['timestamp']} breakout failed: {res.invalid_reasons}")
                
                print(f"Tm thy {len(breakouts)} breakouts hp l theo sau 5 zones u")
            else:
                print("Skipping Layer 6: No zones found in Layer 4")
            
            results["Layer 6"] = "OK"
        except Exception as e:
            print(f" LI Tng 6: {e}")
            results["Layer 6"] = "FAIL"
            root_cause = f"Breakout Detector Error: {e}"

    return print_summary(results, root_cause)

def print_summary(results, root_cause):
    print("\n" + "="*50)
    print("=== DIAGNOSIS SUMMARY ===")
    for layer, status in results.items():
        print(f"{layer}: {status}")
    if "FAIL" in results.values():
         print(f"Root cause: {root_cause}")
    else:
         print("Root cause: Logic is working, but strategy might be too strict over long term.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(debug_backtest())
