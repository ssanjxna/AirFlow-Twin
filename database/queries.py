from database.db import get_connection

def get_all_flights():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM flights")
    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_flight(flight_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM flights WHERE flight_id=?",
        (flight_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return dict(row) if row else None