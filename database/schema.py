import random
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent / "airport.db"

random.seed(42)

AIRLINES = ["Air Mauritius", "Emirates", "British Airways", "Qatar Airways", "IndiGo", "Singapore Airlines"]
ORIGINS = ["MRU", "DXB", "LHR", "DOH", "BOM", "SIN", "JNB", "CDG"]
DESTINATIONS = ["DEL", "MRU", "DXB", "LHR", "SIN", "BOM", "CDG", "JNB"]
GATES = [f"G{n}" for n in range(1, 31)]
STAFF_ROLES = ["Security Officer", "Baggage Handler", "Maintenance Engineer", "Gate Agent", "Supervisor"]
BAGGAGE_STATUS = ["checked_in", "screened", "loaded", "delayed", "missing"]
FLIGHT_STATUS = ["scheduled", "boarding", "departed", "delayed", "cancelled"]
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]

def reset_tables(cursor):
    tables = [
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

    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE flights (
        flight_id TEXT PRIMARY KEY,
        flight_number TEXT,
        airline TEXT,
        origin TEXT,
        destination TEXT,
        scheduled_departure TEXT,
        scheduled_arrival TEXT,
        actual_departure TEXT,
        actual_arrival TEXT,
        gate_id TEXT,
        status TEXT,
        aircraft_type TEXT,
        delay_minutes INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE passengers (
        passenger_id TEXT PRIMARY KEY,
        flight_id TEXT,
        pnr_code TEXT,
        first_name TEXT,
        last_name TEXT,
        nationality TEXT,
        age INTEGER,
        gender TEXT,
        travel_class TEXT,
        checked_in INTEGER,
        boarded INTEGER,
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE baggage (
        baggage_id TEXT PRIMARY KEY,
        passenger_id TEXT,
        flight_id TEXT,
        weight_kg REAL,
        status TEXT,
        checked_in_time TEXT,
        loaded_time TEXT,
        FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE gate_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT,
        gate_id TEXT,
        event_type TEXT,
        event_time TEXT,
        status TEXT,
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE security_screening (
        screening_id INTEGER PRIMARY KEY AUTOINCREMENT,
        passenger_id TEXT,
        flight_id TEXT,
        queue_time_minutes INTEGER,
        screening_time_minutes INTEGER,
        status TEXT,
        screened_at TEXT,
        FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE staff_shifts (
        staff_id TEXT,
        staff_name TEXT,
        role TEXT,
        shift_start TEXT,
        shift_end TEXT,
        assigned_zone TEXT,
        availability_status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE maintenance_logs (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT,
        aircraft_type TEXT,
        issue_type TEXT,
        severity TEXT,
        reported_at TEXT,
        resolved_at TEXT,
        status TEXT,
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE delay_predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT,
        predicted_delay_minutes INTEGER,
        risk_score REAL,
        risk_level TEXT,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE recommendations (
        recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT,
        action TEXT,
        priority TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE simulation_logs (
        simulation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT,
        event TEXT,
        status TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE audit_logs (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT,
        record_id TEXT,
        action TEXT,
        old_value TEXT,
        new_value TEXT,
        changed_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE user_actions (
        action_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action_type TEXT,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE system_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        message TEXT,
        severity TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE model_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT,
        input_summary TEXT,
        output_summary TEXT,
        status TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
