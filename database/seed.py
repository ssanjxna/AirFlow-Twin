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

def seed_data(cursor, num_flights=300):
    now = datetime.now().replace(second=0, microsecond=0)

    flight_ids = []

    for i in range(1, num_flights + 1):
        flight_id = f"SYN-FLT-{i:04d}"
        flight_ids.append(flight_id)

        scheduled_departure = now + timedelta(minutes=random.randint(30, 720))
        scheduled_arrival = scheduled_departure - timedelta(minutes=random.randint(60, 360))

        delay = random.choices(
            [0, 5, 10, 15, 25, 40, 60],
            weights=[35, 20, 15, 12, 10, 5, 3]
        )[0]

        actual_departure = scheduled_departure + timedelta(minutes=delay)
        actual_arrival = scheduled_arrival + timedelta(minutes=random.randint(0, 20))

        cursor.execute("""
        INSERT INTO flights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            flight_id,
            f"AF{random.randint(100, 999)}",
            random.choice(AIRLINES),
            random.choice(ORIGINS),
            random.choice(DESTINATIONS),
            scheduled_departure.isoformat(),
            scheduled_arrival.isoformat(),
            actual_departure.isoformat(),
            actual_arrival.isoformat(),
            random.choice(GATES),
            "delayed" if delay > 15 else random.choice(FLIGHT_STATUS),
            random.choice(["A320", "A350", "B737", "B777", "B787"]),
            delay
        ))

        passenger_count = random.randint(60, 220)

        for p in range(passenger_count):
            passenger_id = f"PAX-{i:04d}-{p:03d}"

            cursor.execute("""
            INSERT INTO passengers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                passenger_id,
                flight_id,
                f"PNR{random.randint(100000, 999999)}",
                f"First{p}",
                f"Last{p}",
                random.choice(["Mauritian", "Indian", "British", "French", "South African", "Singaporean"]),
                random.randint(2, 85),
                random.choice(["M", "F"]),
                random.choice(["Economy", "Premium Economy", "Business"]),
                random.choice([0, 1]),
                random.choice([0, 1])
            ))

            if random.random() < 0.75:
                baggage_id = f"BAG-{i:04d}-{p:03d}"
                checked_time = scheduled_departure - timedelta(minutes=random.randint(60, 240))
                loaded_time = checked_time + timedelta(minutes=random.randint(20, 120))

                cursor.execute("""
                INSERT INTO baggage VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    baggage_id,
                    passenger_id,
                    flight_id,
                    round(random.uniform(7, 32), 2),
                    random.choice(BAGGAGE_STATUS),
                    checked_time.isoformat(),
                    loaded_time.isoformat()
                ))

            cursor.execute("""
            INSERT INTO security_screening (
                passenger_id, flight_id, queue_time_minutes,
                screening_time_minutes, status, screened_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                passenger_id,
                flight_id,
                random.randint(2, 45),
                random.randint(1, 8),
                random.choice(["cleared", "manual_check", "pending"]),
                (scheduled_departure - timedelta(minutes=random.randint(45, 180))).isoformat()
            ))

        for event_type in ["gate_assigned", "boarding_started", "boarding_closed"]:
            cursor.execute("""
            INSERT INTO gate_events (
                flight_id, gate_id, event_type, event_time, status
            )
            VALUES (?, ?, ?, ?, ?)
            """, (
                flight_id,
                random.choice(GATES),
                event_type,
                (scheduled_departure - timedelta(minutes=random.randint(10, 90))).isoformat(),
                random.choice(["completed", "in_progress", "delayed"])
            ))

        if random.random() < 0.35:
            reported_at = scheduled_departure - timedelta(minutes=random.randint(60, 240))
            resolved_at = reported_at + timedelta(minutes=random.randint(15, 120))

            cursor.execute("""
            INSERT INTO maintenance_logs (
                flight_id, aircraft_type, issue_type, severity,
                reported_at, resolved_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                flight_id,
                random.choice(["A320", "A350", "B737", "B777", "B787"]),
                random.choice(["hydraulic_check", "engine_inspection", "cabin_fault", "wheel_check", "sensor_warning"]),
                random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                reported_at.isoformat(),
                resolved_at.isoformat(),
                random.choice(["open", "in_progress", "resolved"])
            ))

        risk_score = min(1.0, round((delay / 60) + random.uniform(0.05, 0.35), 2))

        if risk_score >= 0.75:
            risk_level = "HIGH"
        elif risk_score >= 0.45:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        cursor.execute("""
        INSERT INTO delay_predictions (
            flight_id, predicted_delay_minutes, risk_score, risk_level, reason
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            flight_id,
            max(0, delay + random.randint(-5, 15)),
            risk_score,
            risk_level,
            random.choice([
                "High security queue time",
                "Maintenance task still open",
                "Baggage loading delay",
                "Gate turnaround congestion",
                "Staff availability constraint"
            ])
        ))

        cursor.execute("""
        INSERT INTO recommendations (
            flight_id, action, priority, status
        )
        VALUES (?, ?, ?, ?)
        """, (
            flight_id,
            random.choice([
                "Reassign maintenance crew",
                "Allocate backup baggage team",
                "Move flight to less congested gate",
                "Prioritize security lane allocation",
                "Dispatch supervisor to gate"
            ]),
            risk_level,
            random.choice(["pending", "accepted", "rejected", "completed"])
        ))

        for _ in range(random.randint(3, 8)):
            cursor.execute("""
            INSERT INTO simulation_logs (
                flight_id, event, status
            )
            VALUES (?, ?, ?)
            """, (
                flight_id,
                random.choice([
                    "Aircraft arrived",
                    "Baggage loading started",
                    "Security congestion detected",
                    "Maintenance inspection started",
                    "Delay risk calculated",
                    "Recommendation generated",
                    "Operator reviewed recommendation"
                ]),
                random.choice(["success", "warning", "failed", "pending"])
            ))

        cursor.execute("""
        INSERT INTO model_runs (
            model_name, input_summary, output_summary, status
        )
        VALUES (?, ?, ?, ?)
        """, (
            "synthetic_delay_predictor_v1",
            f"flight_id={flight_id}",
            f"risk={risk_score}, delay={delay}",
            "success"
        ))

    for s in range(1, 151):
        shift_start = now + timedelta(hours=random.randint(-8, 8))
        shift_end = shift_start + timedelta(hours=8)

        cursor.execute("""
        INSERT INTO staff_shifts VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"STAFF-{s:04d}",
            f"Staff Member {s}",
            random.choice(STAFF_ROLES),
            shift_start.isoformat(),
            shift_end.isoformat(),
            random.choice(["Terminal 1", "Terminal 2", "Gate Area", "Security", "Baggage", "Maintenance Bay"]),
            random.choice(["available", "busy", "off_shift"])
        ))

    for i in range(1000):
        cursor.execute("""
        INSERT INTO audit_logs (
            table_name, record_id, action, old_value, new_value, changed_by
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            random.choice(["delay_predictions", "recommendations", "simulation_logs", "flights"]),
            str(random.randint(1, num_flights)),
            random.choice(["INSERT", "UPDATE", "RUN_SIMULATION", "ACCEPT_RECOMMENDATION"]),
            None,
            "Synthetic audit event",
            random.choice(["demo_user", "operator_1", "operator_2", "system"])
        ))

    for i in range(500):
        cursor.execute("""
        INSERT INTO user_actions (
            user_id, action_type, description
        )
        VALUES (?, ?, ?)
        """, (
            random.choice(["operator_1", "operator_2", "admin", "demo_user"]),
            random.choice(["LOGIN", "RUN_SIMULATION", "VIEW_FLIGHT", "ACCEPT_RECOMMENDATION"]),
            "Synthetic user action"
        ))

    for i in range(300):
        cursor.execute("""
        INSERT INTO system_events (
            event_type, message, severity
        )
        VALUES (?, ?, ?)
        """, (
            random.choice(["API_EVENT", "MODEL_EVENT", "DATABASE_EVENT"]),
            random.choice([
                "Simulation completed",
                "Prediction generated",
                "Audit log written",
                "Recommendation stored"
            ]),
            random.choice(["INFO", "WARNING", "ERROR"])
        ))

