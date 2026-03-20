import sqlite3
conn = sqlite3.connect('test.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    table_name = t[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = cursor.fetchall()
    for c in cols:
        name = c[1]
        notnull = c[3]
        if 'is_active' in name:
            print(f"FOUND in TABLE: {table_name}, COLUMN: {name}, NOTNULL: {notnull}")
conn.close()
