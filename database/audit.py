from database.db import get_connection


def log_user_action(user_id, action_type, description):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO user_actions (user_id, action_type, description)
        VALUES (?, ?, ?)
    """, (user_id, action_type, description))

    conn.commit()
    conn.close()


def log_audit(table_name, record_id, action,
              old_value, new_value, changed_by):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (
            table_name,
            record_id,
            action,
            old_value,
            new_value,
            changed_by
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        table_name,
        record_id,
        action,
        old_value,
        new_value,
        changed_by
    ))

    conn.commit()
    conn.close()


def log_model_run(model_name,
                  input_summary,
                  output_summary,
                  status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO model_runs (
            model_name,
            input_summary,
            output_summary,
            status
        )
        VALUES (?, ?, ?, ?)
    """, (
        model_name,
        input_summary,
        output_summary,
        status
    ))

    conn.commit()
    conn.close()


def log_system_event(event_type,
                     message,
                     severity="INFO"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO system_events (
            event_type,
            message,
            severity
        )
        VALUES (?, ?, ?)
    """, (
        event_type,
        message,
        severity
    ))

    conn.commit()
    conn.close()