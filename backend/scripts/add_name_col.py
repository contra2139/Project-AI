import sqlite3
import os

db_path = 'test.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
try:
    conn.execute('ALTER TABLE symbol_strategy_config ADD COLUMN name TEXT')
    conn.commit()
    print("Column 'name' added successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Column 'name' already exists.")
    else:
        print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    conn.close()
