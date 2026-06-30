# backend/audit_logger.py

import sqlite3
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path("database/airflow_audit.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_audit_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_recommendation_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_id TEXT NOT NULL,
        created_at TEXT NOT NULL,

        airport_state_json TEXT NOT NULL,
        gemini_recommendation_json TEXT NOT NULL,

        operator_id TEXT,
        operator_decision TEXT,
        operator_notes TEXT,

        approved_actions_json TEXT,
        rejected_actions_json TEXT,

        final_status TEXT
    )
    """)

    conn.commit()
    conn.close()


def log_ai_recommendation(
    flight_id,
    airport_state,
    gemini_recommendation
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO ai_recommendation_audit (
        flight_id,
        created_at,
        airport_state_json,
        gemini_recommendation_json,
        operator_decision,
        final_status
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        flight_id,
        datetime.utcnow().isoformat() + "Z",
        json.dumps(airport_state),
        json.dumps(gemini_recommendation),
        "PENDING",
        "AWAITING_HUMAN_APPROVAL"
    ))

    audit_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return audit_id


def update_human_decision(
    audit_id,
    operator_id,
    operator_decision,
    operator_notes="",
    approved_actions=None,
    rejected_actions=None
):
    if approved_actions is None:
        approved_actions = []

    if rejected_actions is None:
        rejected_actions = []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE ai_recommendation_audit
    SET
        operator_id = ?,
        operator_decision = ?,
        operator_notes = ?,
        approved_actions_json = ?,
        rejected_actions_json = ?,
        final_status = ?
    WHERE id = ?
    """, (
        operator_id,
        operator_decision,
        operator_notes,
        json.dumps(approved_actions),
        json.dumps(rejected_actions),
        "COMPLETED",
        audit_id
    ))

    conn.commit()
    conn.close()


def get_audit_record(audit_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM ai_recommendation_audit WHERE id = ?",
        (audit_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)