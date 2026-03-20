import sqlite3
import os

db_path = r"E:\Agent_AI_Antigravity\CBX_StrategyV1\test.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get existing columns
cursor.execute("PRAGMA table_info(symbol_strategy_config)")
cols = [row[1] for row in cursor.fetchall()]

new_cols = {
    "long_min_ema_slope": "DECIMAL(10, 6) DEFAULT 0.0003",
    "long_min_price_vs_ema": "DECIMAL(10, 6) DEFAULT 0.005",
    "short_max_ema_slope": "DECIMAL(10, 6) DEFAULT -0.0003",
    "short_max_price_vs_ema": "DECIMAL(10, 6) DEFAULT -0.005",
    "trailing_atr_multiplier": "DECIMAL(5, 2) DEFAULT 1.5"
}

for col, definition in new_cols.items():
    if col not in cols:
        print(f"Adding column {col}...")
        cursor.execute(f"ALTER TABLE symbol_strategy_config ADD COLUMN {col} {definition}")
    else:
        print(f"Column {col} already exists.")

conn.commit()
conn.close()
print("Migration completed.")
