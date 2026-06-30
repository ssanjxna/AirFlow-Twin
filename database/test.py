from database.db import get_connection

REQUIRED_TABLES = [
    "flights",
    "passengers",
    "baggage",
    "gate_events",
    "security_screening",
    "staff_shifts",
    "maintenance_logs",
    "delay_predictions",
    "recommendations",
    "simulation_logs",
    "audit_logs",
    "user_actions",
    "system_events",
    "model_runs",
]

def check_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row["name"] for row in cursor.fetchall()}

    print("\n=== TABLE CHECK ===")
    for table in REQUIRED_TABLES:
        if table in existing_tables:
            print(f"[OK] {table}")
        else:
            print(f"[MISSING] {table}")

def check_row_counts(cursor):
    print("\n=== ROW COUNTS ===")
    for table in REQUIRED_TABLES:
        try:
            cursor.execute(f"SELECT COUNT(*) AS count FROM {table}")
            count = cursor.fetchone()["count"]
            print(f"{table}: {count}")
        except Exception as e:
            print(f"{table}: ERROR - {e}")

def check_sample_flight(cursor):
    print("\n=== SAMPLE FLIGHT ===")
    try:
        cursor.execute("SELECT * FROM flights LIMIT 1")
        row = cursor.fetchone()

        if row:
            print(dict(row))
        else:
            print("No flights found.")
    except Exception as e:
        print("ERROR:", e)

def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("Connected to database successfully.")

    check_tables(cursor)
    check_row_counts(cursor)
    check_sample_flight(cursor)

    conn.close()

    print("\nDatabase test completed.")

if __name__ == "__main__":
    main()