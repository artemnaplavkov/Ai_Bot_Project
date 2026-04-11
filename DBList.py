import sqlite3
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

cursor.execute("SELECT * FROM logs;")
for row in cursor.fetchall():
    print(row)

print("\n")

cursor.execute("SELECT * FROM users;")
print(cursor.fetchall())

conn.close()