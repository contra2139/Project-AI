import sqlite3
import uuid
from datetime import datetime

DB_PATH = r'e:\Agent_AI_Antigravity\CBX_StrategyV1\test.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Starting Migration to V4 ---")
    
    # 1. Add column if not exists
    try:
        cursor.execute("ALTER TABLE symbol_strategy_config ADD COLUMN entry_retest_buffer_atr DECIMAL(5, 3) DEFAULT 0.05")
        print("Added column entry_retest_buffer_atr")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column entry_retest_buffer_atr already exists")
        else:
            raise e

    # 2. Deactivate current configs
    cursor.execute("UPDATE symbol_strategy_config SET is_current = 0")
    
    # 3. Get symbol IDs
    symbols = {
        'BTCUSDC': 'bd1d0c1d-8564-40cb-a6d0-89376ebfa96a',
        'BNBUSDC': '4ee9a736-42a6-4b75-9544-28db55a9e0a3',
        'SOLUSDC': 'b775c169-9492-476b-8a64-6f7ad8b83adf'
    }
    
    # Common parameters for V4
    v4_params = {
        'version': 4,
        'is_current': 1,
        'created_by': 'Antigravity',
        'time_stop_bars': 30,
        'partial_exit_pct': 30.0,
        'partial_exit_r_level': 0.8,
        'stop_loss_atr_buffer': 0.20,
        'change_reason': 'V4: Extended Time Stop (30), Reduced Partial (30%), Earlier Partial (0.8R), Tighter SL (0.20)'
    }
    
    # Fetch a template from V3 (or existing) to preserve other parameters
    cursor.execute("SELECT * FROM symbol_strategy_config WHERE version < 4 ORDER BY created_at DESC LIMIT 1")
    template_row = cursor.fetchone()
    
    # Get column names
    col_names = [description[0] for description in cursor.description]
    
    for sym_name, sym_id in symbols.items():
        print(f"Migrating {sym_name} to V4...")
        
        # Create new config based on template
        new_values = list(template_row)
        new_config_id = str(uuid.uuid4()).replace('-', '') # SQLite UUIDs are often stored as hex strings
        
        # Map values to columns
        val_map = dict(zip(col_names, new_values))
        val_map.update(v4_params)
        val_map['symbol_id'] = sym_id.replace('-', '')
        val_map['strategy_config_id'] = str(uuid.uuid4()).replace('-', '')
        val_map['created_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # SOL specific
        if sym_name == 'SOLUSDC':
            val_map['entry_retest_buffer_atr'] = 0.10
        else:
            val_map['entry_retest_buffer_atr'] = 0.05
            
        # SQL Insert
        cols = ", ".join(val_map.keys())
        placeholders = ", ".join(["?"] * len(val_map))
        sql = f"INSERT INTO symbol_strategy_config ({cols}) VALUES ({placeholders})"
        cursor.execute(sql, list(val_map.values()))
    
    conn.commit()
    print("Migration COMPLETED.")
    conn.close()

if __name__ == "__main__":
    migrate()
