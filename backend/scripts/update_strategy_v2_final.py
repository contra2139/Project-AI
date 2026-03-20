import sqlite3

db_path = 'test.db'
conn = sqlite3.connect(db_path)
try:
    # 1. Update Version 2 configs with the LOOSENED thresholds
    conn.execute("""
        UPDATE symbol_strategy_config 
        SET 
            breakout_volume_ratio_min = 1.10,
            breakout_volume_percentile_min = 60.0,
            breakout_close_position_long = 0.65,
            breakout_close_position_short = 0.35,
            breakout_body_ratio_min = 0.50,
            change_reason = 'V2 Final: Loosened for 15m Momentum'
        WHERE version = 2
    """)
    conn.commit()
    print("Strategy Version 2 thresholds updated to Momentum-Loosened (1.1x Vol, 0.5x Body)!")
    
    # 2. Confirm current active versions
    res = conn.execute("SELECT symbol, version, is_current FROM symbol_strategy_config JOIN symbol_registry ON symbol_strategy_config.symbol_id = symbol_registry.symbol_id").fetchall()
    for row in res:
        print(f"Symbol: {row[0]}, Version: {row[1]}, Current: {row[2]}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
