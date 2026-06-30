from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

print("Connected to database.")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Found {len(tables)} tables:")

for table in tables:
    print("-", table["name"])

conn.close()