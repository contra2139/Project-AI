import sqlite3
import uuid
import os

DB_PATH = 'test.db'

def fix():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Register other symbols if missing
    symbols_to_register = [
        ('BNBUSDC', 'BNB', 'USDC', 'BINANCE', 'PERP'),
        ('SOLUSDC', 'SOL', 'USDC', 'BINANCE', 'PERP')
    ]
    for sym, base, quote, ex, ctype in symbols_to_register:
        cursor.execute("SELECT symbol_id FROM symbol_registry WHERE symbol = ?", (sym,))
        if not cursor.fetchone():
            print(f"Registering {sym}...")
            cursor.execute("INSERT INTO symbol_registry (symbol_id, symbol, base_asset, quote_asset, exchange, contract_type) VALUES (?, ?, ?, ?, ?, ?)",
                           (str(uuid.uuid4()), sym, base, quote, ex, ctype))

    # 2. Sync Configuration Schema
    required_columns = {
        'bb_period': 'INTEGER DEFAULT 20',
        'bb_std': 'DECIMAL(4, 2) DEFAULT 2.0',
        'bb_width_percentile_threshold': 'DECIMAL(5, 2) DEFAULT 20.0',
        'compression_min_bars': 'INTEGER DEFAULT 8',
        'compression_max_bars': 'INTEGER DEFAULT 24',
        'min_conditions_met': 'INTEGER DEFAULT 3',
        'breakout_distance_min_atr': 'DECIMAL(5, 3) DEFAULT 0.20',
        'breakout_body_ratio_min': 'DECIMAL(5, 3) DEFAULT 0.60',
        'breakout_close_position_long': 'DECIMAL(5, 3) DEFAULT 0.75',
        'breakout_close_position_short': 'DECIMAL(5, 3) DEFAULT 0.25',
        'breakout_volume_ratio_min': 'DECIMAL(5, 3) DEFAULT 1.30',
        'breakout_volume_percentile_min': 'DECIMAL(5, 2) DEFAULT 70.0',
        'breakout_bar_size_max_atr': 'DECIMAL(5, 2) DEFAULT 2.50',
        'false_break_limit': 'INTEGER DEFAULT 2',
        'expansion_lookforward_bars': 'INTEGER DEFAULT 3',
        'expansion_body_loss_max_pct': 'DECIMAL(5, 2) DEFAULT 50.0',
        'retest_max_bars': 'INTEGER DEFAULT 3',
        'max_position_per_symbol': 'INTEGER DEFAULT 1',
        'ema_period_context': 'INTEGER DEFAULT 50',
        'context_timeframe': 'VARCHAR(5) DEFAULT "1h"',
        'execution_timeframe': 'VARCHAR(5) DEFAULT "15m"',
        'atr_percentile_window': 'INTEGER DEFAULT 120',
        'range_bars': 'INTEGER DEFAULT 12'
    }

    cursor.execute("PRAGMA table_info(symbol_strategy_config)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    for col_name, sql_type in required_columns.items():
        if col_name not in existing_columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE symbol_strategy_config ADD COLUMN {col_name} {sql_type}")

    # 3. Parameters for V4
    v4_values = {
        'time_stop_bars': 30,
        'partial_exit_pct': 0.30,
        'partial_exit_r_level': 0.80,
        'stop_loss_atr_buffer': 0.20,
        'atr_period': 14,
        'atr_percentile_threshold': 20.0,
        'range_percentile_threshold': 20.0,
        'bb_width_percentile_threshold': 20.0,
        'volume_percentile_threshold': 60.0,
        'compression_min_bars': 8,
        'compression_max_bars': 24,
        'min_conditions_met': 3,
        'breakout_distance_min_atr': 0.20,
        'breakout_body_ratio_min': 0.50,
        'breakout_close_position_long': 0.65,
        'breakout_close_position_short': 0.35,
        'breakout_volume_ratio_min': 1.10,
        'breakout_volume_percentile_min': 60.0,
        'breakout_bar_size_max_atr': 2.50,
        'false_break_limit': 2,
        'expansion_lookforward_bars': 3,
        'expansion_body_loss_max_pct': 50.0,
        'retest_max_bars': 3,
        'risk_per_trade_pct': 0.0025,
        'max_position_per_symbol': 1,
        'ema_period_context': 50,
        'context_timeframe': '1h',
        'execution_timeframe': '15m',
        'version': 4,
        'is_current': 1,
        'created_by': 'RESEARCHER'
    }

    cursor.execute("SELECT symbol_id, symbol FROM symbol_registry")
    all_symbols = cursor.fetchall()

    for symbol_id, symbol in all_symbols:
        print(f"Checking {symbol} Strategy V4...")
        cursor.execute("SELECT strategy_config_id FROM symbol_strategy_config WHERE symbol_id = ? AND version = 4", (symbol_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"Inserting V4 for {symbol}...")
            v4_params = v4_values.copy()
            v4_params['strategy_config_id'] = str(uuid.uuid4())
            v4_params['symbol_id'] = symbol_id
            v4_params['name'] = f"{symbol} V4 Optimization"
            
            # Deactivate all others
            cursor.execute("UPDATE symbol_strategy_config SET is_current = 0 WHERE symbol_id = ?", (symbol_id,))
            
            columns = ', '.join(v4_params.keys())
            placeholders = ', '.join(['?' for _ in v4_params])
            cursor.execute(f"INSERT INTO symbol_strategy_config ({columns}) VALUES ({placeholders})", tuple(v4_params.values()))
        else:
            print(f"Updating V4 for {symbol}...")
            # Set all others to false
            cursor.execute("UPDATE symbol_strategy_config SET is_current = 0 WHERE symbol_id = ?", (symbol_id,))
            
            # Update values and set is_current = 1
            set_clause = ', '.join([f"{k} = ?" for k in v4_values.keys()])
            sql = f"UPDATE symbol_strategy_config SET {set_clause} WHERE symbol_id = ? AND version = 4"
            cursor.execute(sql, tuple(v4_values.values()) + (symbol_id,))

    conn.commit()

    # 4. Verify
    print("\n=== Final Active Strategy Configs ===")
    cursor.execute("""
        SELECT s.symbol, c.version, c.is_current, c.time_stop_bars, c.risk_per_trade_pct
        FROM symbol_strategy_config c
        JOIN symbol_registry s USING (symbol_id)
        WHERE c.is_current = 1;
    """)
    for row in cursor.fetchall():
        print(f"Symbol: {row[0]} | Version: {row[1]} | Current: {row[2]} | TimeStop: {row[3]} | Risk: {row[4]}")

    conn.close()

if __name__ == "__main__":
    fix()
