from fastapi import FastAPI
from database.db import get_connection
from database.audit import log_user_action, log_audit, log_model_run

app = FastAPI(title="AirFlow Twin API")


@app.get("/")
def root():
    return {"message": "AirFlow Twin API running"}


@app.post("/simulate")
def simulate():
    user_id = "demo_user"

    log_user_action(
        user_id,
        "RUN_SIMULATION",
        "User triggered delay simulation"
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM flights LIMIT 1")
    flight = cursor.fetchone()

    if not flight:
        conn.close()
        return {"error": "No flights found"}

    flight = dict(flight)
    flight_id = flight.get("flight_id") or flight.get("id") or "UNKNOWN"

    predicted_delay = 18
    risk_score = 0.87
    risk_level = "HIGH"
    reason = "Maintenance workload and gate activity indicate possible turnaround delay."

    cursor.execute("""
        INSERT INTO delay_predictions (
            flight_id, predicted_delay_minutes, risk_score, risk_level, reason
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        flight_id,
        predicted_delay,
        risk_score,
        risk_level,
        reason
    ))

    prediction_id = cursor.lastrowid

    action = "Prioritize maintenance crew and monitor gate turnaround activity."
    priority = "HIGH"

    cursor.execute("""
        INSERT INTO recommendations (
            flight_id, action, priority, status
        )
        VALUES (?, ?, ?, ?)
    """, (
        flight_id,
        action,
        priority,
        "pending"
    ))

    recommendation_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO simulation_logs (
            flight_id, event, status
        )
        VALUES (?, ?, ?)
    """, (
        flight_id,
        "Simulation completed",
        "success"
    ))

    conn.commit()
    conn.close()

    log_audit(
        "delay_predictions",
        str(prediction_id),
        "INSERT",
        None,
        f"Prediction created for flight {flight_id}",
        user_id
    )

    log_audit(
        "recommendations",
        str(recommendation_id),
        "INSERT",
        None,
        f"Recommendation created for flight {flight_id}",
        user_id
    )

    log_model_run(
        "simple_rule_based_simulator",
        f"flight_id={flight_id}",
        f"delay={predicted_delay}, risk={risk_score}",
        "success"
    )

    return {
        "flight_id": flight_id,
        "prediction": {
            "prediction_id": prediction_id,
            "predicted_delay_minutes": predicted_delay,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "reason": reason
        },
        "recommendation": {
            "recommendation_id": recommendation_id,
            "action": action,
            "priority": priority,
            "status": "pending"
        }
    }