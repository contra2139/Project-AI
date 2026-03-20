import sqlite3
import uuid
import datetime

DB_PATH = "test.db"

def update_to_v2():
    print("🚀 Starting Strategy v2 Migration (Raw SQL)...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Clean up old v2
        print("🧹 Cleaning up version 2 records...")
        cursor.execute("DELETE FROM symbol_strategy_config WHERE version=2")
        
        # 2. Find current v1 configs
        cursor.execute("SELECT * FROM symbol_strategy_config WHERE is_current=1")
        v1_configs = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(symbol_strategy_config)")
        cols = [c[1] for c in cursor.fetchall()]
        
        for v1_row in v1_configs:
            # Map v1_row to dict for easy access
            config = dict(zip(cols, v1_row))
            symbol_id = config['symbol_id']
            
            print(f"--- Processing {symbol_id} ---")
            
            # 3. Deactivate v1
            cursor.execute("UPDATE symbol_strategy_config SET is_current=0 WHERE strategy_config_id=?", (config['strategy_config_id'],))
            
            # 4. Create v2 record
            new_id = uuid.uuid4().hex
            v2 = config.copy()
            v2['strategy_config_id'] = new_id
            v2['version'] = 2
            v2['is_current'] = 1
            v2['created_at'] = datetime.datetime.utcnow().isoformat()
            v2['created_by'] = 'AI_Antigravity'
            v2['based_on_version'] = 1
            v2['change_reason'] = 'Loosen filters for 15m timeframe'
            
            # UPDATED PARAMETERS per User Request
            v2['breakout_volume_ratio_min'] = 1.10
            v2['breakout_volume_percentile_min'] = 60.0
            v2['breakout_close_position_long'] = 0.65
            v2['breakout_close_position_short'] = 0.35
            v2['breakout_body_ratio_min'] = 0.50
            
            # Construct INSERT statement
            keys = v2.keys()
            placeholders = ", ".join(["?"] * len(keys))
            columns = ", ".join(keys)
            values = [v2[k] for k in keys]
            
            insert_sql = f"INSERT INTO symbol_strategy_config ({columns}) VALUES ({placeholders})"
            cursor.execute(insert_sql, values)
            print(f"✅ Created v2 for {symbol_id} (New ID: {new_id})")
            
        conn.commit()
        print("\n🎉 Strategy v2 Migration Complete!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration FAILED: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    update_to_v2()
