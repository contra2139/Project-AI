import sqlite3
conn = sqlite3.connect('test.db')
cursor = conn.cursor()
cursor.execute("SELECT sql FROM sqlite_master WHERE name='trade'")
row = cursor.fetchone()
if row:
    print(row[0])
else:
    print("Table 'trade' not found")
conn.close()
