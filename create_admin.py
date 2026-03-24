import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT;")
    print("Successfully added the column 'reset_token'.")
except sqlite3.OperationalError as e:
    print("Column may already exist:", e)

conn.commit()
conn.close()