from database.db import get_connection
from database.schema import reset_tables, create_tables
from database.seed import seed_data

def main():
    conn = get_connection()
    cursor = conn.cursor()

    print("Resetting tables...")
    reset_tables(cursor)

    print("Creating schema...")
    create_tables(cursor)

    print("Seeding synthetic data...")
    seed_data(cursor, num_flights=300)

    conn.commit()
    conn.close()

    print("Database initialized successfully.")

if __name__ == "__main__":
    main()