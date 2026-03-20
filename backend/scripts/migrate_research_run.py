import sqlite3
import os
import sys

# Thêm đường dẫn gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

db_path = r"E:\Agent_AI_Antigravity\CBX_StrategyV1\test.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Kiểm tra cột hiện có
    cursor.execute("PRAGMA table_info(research_run)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"Existing columns: {cols}")

    # Thêm cột còn thiếu nếu chưa có
    missing = {
        "entry_model":  "ALTER TABLE research_run ADD COLUMN entry_model TEXT",
        "side_filter":  "ALTER TABLE research_run ADD COLUMN side_filter TEXT",
    }

    for col, sql in missing.items():
        if col not in cols:
            cursor.execute(sql)
            print(f"Added column: {col}")
        else:
            print(f"Column already exists: {col}")

    conn.commit()
    conn.close()
    print("Done. Run backtest now.")

if __name__ == "__main__":
    migrate()
