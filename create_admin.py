import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("""
UPDATE users
SET password = ?
WHERE email = ?
""", ("Olafaith'z1856", "oladipupoaustin1856@gmail.com"))

conn.commit()
conn.close()