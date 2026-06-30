from database.db import get_connection

conn = get_connection()
cursor = conn.cursor()

print("Connected to database.")

# Show all tables first
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("\nAvailable tables:")
for table in tables:
    print("-", table["name"])

# Change 'flights' to any table you know exists
table_name = "flights"

print(f"\nTrying to read from '{table_name}'...")

try:
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
    rows = cursor.fetchall()

    print(f"Found {len(rows)} rows:\n")

    for row in rows:
        print(dict(row))

except Exception as e:
    print("ERROR:", e)

conn.close()