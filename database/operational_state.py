import json
import uuid
from datetime import UTC, datetime

from database.db import get_connection


def _utc_now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _dumps(value):
    return json.dumps(value or {}, sort_keys=True)


def _loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def ensure_operational_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS flight_decision_state (
            flight_id TEXT PRIMARY KEY,
            flight_snapshot_json TEXT NOT NULL,
            baseline_risk_percent REAL NOT NULL,
            baseline_confidence_percent INTEGER NOT NULL,
            baseline_predicted_delay_minutes INTEGER NOT NULL,
            current_risk_percent REAL NOT NULL,
            current_confidence_percent INTEGER NOT NULL,
            current_predicted_delay_minutes INTEGER NOT NULL,
            total_risk_reduced REAL NOT NULL DEFAULT 0,
            total_delay_saved INTEGER NOT NULL DEFAULT 0,
            total_actions_completed INTEGER NOT NULL DEFAULT 0,
            risk_cause TEXT,
            executive_summary TEXT,
            airport_state_json TEXT,
            recommendation_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_actions (
            action_id TEXT PRIMARY KEY,
            flight_id TEXT NOT NULL,
            recommendation_id INTEGER,
            action_text TEXT NOT NULL,
            impact_text TEXT,
            target_team TEXT,
            priority TEXT,
            delay_reduction_minutes INTEGER NOT NULL DEFAULT 0,
            risk_reduction_percent INTEGER NOT NULL DEFAULT 0,
            validation_required INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (flight_id) REFERENCES flight_decision_state(flight_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_executions (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id TEXT NOT NULL,
            applied_action_ids_json TEXT NOT NULL,
            applied_action_texts_json TEXT NOT NULL,
            before_risk_percent REAL NOT NULL,
            after_risk_percent REAL NOT NULL,
            before_confidence_percent INTEGER NOT NULL,
            after_confidence_percent INTEGER NOT NULL,
            before_delay_minutes INTEGER NOT NULL,
            after_delay_minutes INTEGER NOT NULL,
            total_risk_reduction REAL NOT NULL,
            total_delay_saved INTEGER NOT NULL,
            operator_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (flight_id) REFERENCES flight_decision_state(flight_id)
        )
        """
    )

    conn.commit()
    conn.close()


def _fetch_state(cursor, flight_id):
    cursor.execute(
        "SELECT * FROM flight_decision_state WHERE flight_id = ?",
        (flight_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _fetch_actions(cursor, flight_id, statuses=None):
    query = "SELECT * FROM recommendation_actions WHERE flight_id = ?"
    params = [flight_id]

    if statuses:
        placeholders = ", ".join(["?"] * len(statuses))
        query += f" AND status IN ({placeholders})"
        params.extend(statuses)

    query += " ORDER BY created_at, action_id"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


def _serialize_action(row):
    return {
        "id": row["action_id"],
        "text": row["action_text"],
        "impact": row["impact_text"],
        "target_team": row["target_team"],
        "priority": row["priority"],
        "delay_reduction": int(row["delay_reduction_minutes"]),
        "risk_reduction": int(row["risk_reduction_percent"]),
        "validation_required": bool(row["validation_required"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def sync_flight_state(
    flight,
    risk_cause="",
    executive_summary="",
    airport_state=None,
    recommendation=None,
):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    flight_id = flight["id"]
    now = _utc_now()
    state = _fetch_state(cursor, flight_id)

    if state is None:
        cursor.execute(
            """
            INSERT INTO flight_decision_state (
                flight_id,
                flight_snapshot_json,
                baseline_risk_percent,
                baseline_confidence_percent,
                baseline_predicted_delay_minutes,
                current_risk_percent,
                current_confidence_percent,
                current_predicted_delay_minutes,
                total_risk_reduced,
                total_delay_saved,
                total_actions_completed,
                risk_cause,
                executive_summary,
                airport_state_json,
                recommendation_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                flight_id,
                _dumps(flight),
                float(flight.get("risk", 0)),
                int(flight.get("confidence_percent", 0)),
                int(flight.get("predicted_delay_minutes", 0)),
                float(flight.get("risk", 0)),
                int(flight.get("confidence_percent", 0)),
                int(flight.get("predicted_delay_minutes", 0)),
                risk_cause,
                executive_summary,
                _dumps(airport_state or {}),
                _dumps(recommendation or {}),
                now,
                now,
            ),
        )
    else:
        cursor.execute(
            """
            UPDATE flight_decision_state
            SET
                flight_snapshot_json = ?,
                risk_cause = COALESCE(?, risk_cause),
                executive_summary = COALESCE(?, executive_summary),
                airport_state_json = COALESCE(?, airport_state_json),
                recommendation_json = COALESCE(?, recommendation_json),
                updated_at = ?
            WHERE flight_id = ?
            """,
            (
                _dumps(flight),
                risk_cause or None,
                executive_summary or None,
                _dumps(airport_state or {}) if airport_state else None,
                _dumps(recommendation or {}) if recommendation else None,
                now,
                flight_id,
            ),
        )

    conn.commit()
    state = _fetch_state(cursor, flight_id)
    conn.close()
    return state


def overlay_persisted_state(flight):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    state = _fetch_state(cursor, flight["id"])
    conn.close()

    if state is None:
        return flight

    return {
        **flight,
        "risk": int(round(float(state["current_risk_percent"]))),
        "confidence_percent": int(state["current_confidence_percent"]),
        "predicted_delay_minutes": int(state["current_predicted_delay_minutes"]),
    }


def ensure_recommendation_actions(flight_id, recommendations):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    existing = _fetch_actions(cursor, flight_id)

    if existing:
        conn.close()
        return [_serialize_action(row) for row in existing]

    now = _utc_now()
    for recommendation in recommendations or []:
        cursor.execute(
            """
            INSERT INTO recommendations (
                flight_id,
                action,
                priority,
                status
            )
            VALUES (?, ?, ?, 'pending')
            """,
            (
                flight_id,
                recommendation.get("text", "Operational mitigation"),
                recommendation.get("priority", "High"),
            ),
        )
        recommendation_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO recommendation_actions (
                action_id,
                flight_id,
                recommendation_id,
                action_text,
                impact_text,
                target_team,
                priority,
                delay_reduction_minutes,
                risk_reduction_percent,
                validation_required,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                str(uuid.uuid4()),
                flight_id,
                recommendation_id,
                recommendation.get("text", "Operational mitigation"),
                recommendation.get("impact", ""),
                recommendation.get("target_team", "Operations"),
                recommendation.get("priority", "High"),
                int(recommendation.get("delay_reduction", 0)),
                int(recommendation.get("risk_reduction", 0)),
                1 if recommendation.get("validation_required", True) else 0,
                now,
            ),
        )

    conn.commit()
    created = _fetch_actions(cursor, flight_id)
    conn.close()
    return [_serialize_action(row) for row in created]


def get_open_recommendations(flight_id):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    rows = _fetch_actions(cursor, flight_id, statuses=["pending"])
    conn.close()
    return [_serialize_action(row) for row in rows]


def get_flight_analysis_state(flight_id):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    state = _fetch_state(cursor, flight_id)
    open_actions = _fetch_actions(cursor, flight_id, statuses=["pending"])
    completed_actions = _fetch_actions(cursor, flight_id, statuses=["completed"])
    conn.close()

    if state is None:
        return None

    current_risk = float(state["current_risk_percent"])
    current_delay = int(state["current_predicted_delay_minutes"])
    current_confidence = int(state["current_confidence_percent"])
    total_open_risk = sum(int(row["risk_reduction_percent"]) for row in open_actions)
    total_open_delay = sum(int(row["delay_reduction_minutes"]) for row in open_actions)

    return {
        "state": state,
        "open_recommendations": [_serialize_action(row) for row in open_actions],
        "completed_recommendations": [_serialize_action(row) for row in completed_actions],
        "expected_impact": {
            "current_overall_risk_percent": round(current_risk, 2),
            "estimated_risk_after_actions_percent": round(max(0.0, current_risk - total_open_risk), 2),
            "estimated_delay_reduction_minutes": int(total_open_delay),
            "current_confidence_percent": current_confidence,
        },
    }


def apply_recommendations(flight_id, action_ids, operator_id="demo_user"):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()

    state = _fetch_state(cursor, flight_id)
    if state is None:
        conn.close()
        raise ValueError(f"No persisted state found for flight {flight_id}.")

    if not action_ids:
        conn.close()
        raise ValueError("No recommendation actions were selected.")

    placeholders = ", ".join(["?"] * len(action_ids))
    cursor.execute(
        f"""
        SELECT * FROM recommendation_actions
        WHERE flight_id = ?
          AND status = 'pending'
          AND action_id IN ({placeholders})
        ORDER BY created_at, action_id
        """,
        (flight_id, *action_ids),
    )
    actions = [dict(row) for row in cursor.fetchall()]

    if not actions:
        conn.close()
        raise ValueError("Selected recommendations are no longer pending.")

    before_risk = float(state["current_risk_percent"])
    before_confidence = int(state["current_confidence_percent"])
    before_delay = int(state["current_predicted_delay_minutes"])
    total_risk_reduction = sum(int(action["risk_reduction_percent"]) for action in actions)
    total_delay_saved = sum(int(action["delay_reduction_minutes"]) for action in actions)
    confidence_reduction = max(len(actions) * 2, int(round(total_risk_reduction * 0.4)))
    after_risk = max(0.0, before_risk - total_risk_reduction)
    after_delay = max(0, before_delay - total_delay_saved)
    after_confidence = max(5, before_confidence - confidence_reduction)
    now = _utc_now()

    cursor.execute(
        """
        UPDATE flight_decision_state
        SET
            current_risk_percent = ?,
            current_confidence_percent = ?,
            current_predicted_delay_minutes = ?,
            total_risk_reduced = total_risk_reduced + ?,
            total_delay_saved = total_delay_saved + ?,
            total_actions_completed = total_actions_completed + ?,
            updated_at = ?
        WHERE flight_id = ?
        """,
        (
            round(after_risk, 2),
            after_confidence,
            after_delay,
            total_risk_reduction,
            total_delay_saved,
            len(actions),
            now,
            flight_id,
        ),
    )

    action_texts = []
    for action in actions:
        action_texts.append(action["action_text"])
        cursor.execute(
            """
            UPDATE recommendation_actions
            SET status = 'completed', completed_at = ?
            WHERE action_id = ?
            """,
            (now, action["action_id"]),
        )
        if action["recommendation_id"]:
            cursor.execute(
                """
                UPDATE recommendations
                SET status = 'completed'
                WHERE recommendation_id = ?
                """,
                (action["recommendation_id"],),
            )

    cursor.execute(
        """
        INSERT INTO recommendation_executions (
            flight_id,
            applied_action_ids_json,
            applied_action_texts_json,
            before_risk_percent,
            after_risk_percent,
            before_confidence_percent,
            after_confidence_percent,
            before_delay_minutes,
            after_delay_minutes,
            total_risk_reduction,
            total_delay_saved,
            operator_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            flight_id,
            json.dumps([action["action_id"] for action in actions]),
            json.dumps(action_texts),
            before_risk,
            after_risk,
            before_confidence,
            after_confidence,
            before_delay,
            after_delay,
            total_risk_reduction,
            total_delay_saved,
            operator_id,
            now,
        ),
    )

    cursor.execute(
        """
        INSERT INTO delay_predictions (
            flight_id,
            predicted_delay_minutes,
            risk_score,
            risk_level,
            reason
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            flight_id,
            after_delay,
            round(after_risk / 100, 4),
            "HIGH" if after_risk >= 80 else "MEDIUM" if after_risk >= 50 else "LOW",
            f"Applied {len(actions)} AI recommendation(s).",
        ),
    )

    cursor.execute(
        """
        INSERT INTO simulation_logs (
            flight_id,
            event,
            status
        )
        VALUES (?, ?, ?)
        """,
        (
            flight_id,
            f"Applied AI recommendations: {', '.join(action_texts)}",
            "success",
        ),
    )

    old_value = json.dumps(
        {
            "risk_percent": before_risk,
            "confidence_percent": before_confidence,
            "predicted_delay_minutes": before_delay,
        }
    )
    new_value = json.dumps(
        {
            "risk_percent": round(after_risk, 2),
            "confidence_percent": after_confidence,
            "predicted_delay_minutes": after_delay,
            "actions": action_texts,
        }
    )

    cursor.execute(
        """
        INSERT INTO audit_logs (
            table_name,
            record_id,
            action,
            old_value,
            new_value,
            changed_by
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "flight_decision_state",
            flight_id,
            "APPLY_RECOMMENDATIONS",
            old_value,
            new_value,
            operator_id,
        ),
    )

    cursor.execute(
        """
        INSERT INTO user_actions (
            user_id,
            action_type,
            description
        )
        VALUES (?, ?, ?)
        """,
        (
            operator_id,
            "APPLY_RECOMMENDATIONS",
            f"Applied {len(actions)} recommendation(s) for {flight_id}",
        ),
    )

    cursor.execute(
        """
        INSERT INTO model_runs (
            model_name,
            input_summary,
            output_summary,
            status
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "airflow_action_impact_v1",
            f"flight_id={flight_id};actions={len(actions)}",
            f"before_risk={before_risk};after_risk={after_risk};saved={total_delay_saved}",
            "success",
        ),
    )

    conn.commit()
    updated_state = _fetch_state(cursor, flight_id)
    remaining_actions = _fetch_actions(cursor, flight_id, statuses=["pending"])
    conn.close()

    return {
        "state": updated_state,
        "remaining_recommendations": [_serialize_action(row) for row in remaining_actions],
        "applied_actions": [_serialize_action(row) for row in actions],
    }


def get_impact_summary():
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flight_decision_state ORDER BY updated_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) AS count FROM recommendation_actions")
    total_actions = int(cursor.fetchone()["count"])
    cursor.execute("SELECT COUNT(*) AS count FROM recommendation_actions WHERE status = 'completed'")
    completed_actions = int(cursor.fetchone()["count"])
    conn.close()

    if not rows:
        return {
            "before_delayed": 0,
            "after_delayed": 0,
            "before_total_delay": 0,
            "after_total_delay": 0,
            "total_time_saved": 0,
            "efficiency_improvement": 0,
            "resource_optimization": 0,
            "cost_savings_k": 0.0,
            "passenger_satisfaction_gain": 0,
            "completed_actions": 0,
            "total_actions": 0,
        }

    before_delayed = sum(1 for row in rows if int(row["baseline_predicted_delay_minutes"]) >= 15)
    after_delayed = sum(1 for row in rows if int(row["current_predicted_delay_minutes"]) >= 15)
    before_total_delay = sum(int(row["baseline_predicted_delay_minutes"]) for row in rows)
    after_total_delay = sum(int(row["current_predicted_delay_minutes"]) for row in rows)
    total_time_saved = max(0, before_total_delay - after_total_delay)
    efficiency = int(round((total_time_saved / before_total_delay) * 100)) if before_total_delay else 0
    resource = int(round((completed_actions / total_actions) * 100)) if total_actions else 0
    cost_savings_k = round(total_time_saved * 0.08, 1)
    satisfaction = min(40, max(0, int(round(efficiency * 0.45 + completed_actions * 1.5))))

    return {
        "before_delayed": before_delayed,
        "after_delayed": after_delayed,
        "before_total_delay": before_total_delay,
        "after_total_delay": after_total_delay,
        "total_time_saved": total_time_saved,
        "efficiency_improvement": efficiency,
        "resource_optimization": resource,
        "cost_savings_k": cost_savings_k,
        "passenger_satisfaction_gain": satisfaction,
        "completed_actions": completed_actions,
        "total_actions": total_actions,
    }


def get_audit_feed(limit=50):
    ensure_operational_tables()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM recommendation_executions
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    executions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    feed = []
    for execution in executions:
        feed.append(
            {
                "timestamp": execution["created_at"],
                "flight_id": execution["flight_id"],
                "operator_id": execution["operator_id"],
                "actions": _loads(execution["applied_action_texts_json"], []),
                "before_risk_percent": round(float(execution["before_risk_percent"]), 2),
                "after_risk_percent": round(float(execution["after_risk_percent"]), 2),
                "before_confidence_percent": int(execution["before_confidence_percent"]),
                "after_confidence_percent": int(execution["after_confidence_percent"]),
                "before_delay_minutes": int(execution["before_delay_minutes"]),
                "after_delay_minutes": int(execution["after_delay_minutes"]),
                "total_risk_reduction": round(float(execution["total_risk_reduction"]), 2),
                "total_delay_saved": int(execution["total_delay_saved"]),
            }
        )

    return feed
