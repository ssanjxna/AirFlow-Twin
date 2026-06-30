import importlib
import sqlite3
import sys

import pytest


@pytest.fixture
def live_client(monkeypatch):
    db_uri = "file:airflow_test?mode=memory&cache=shared"
    keeper = sqlite3.connect(db_uri, uri=True)
    keeper.row_factory = sqlite3.Row

    schema = importlib.import_module("database.schema")
    db_module = importlib.import_module("database.db")
    operational_state = importlib.import_module("database.operational_state")

    schema.create_tables(keeper.cursor())
    keeper.commit()

    def fake_get_connection():
        conn = sqlite3.connect(db_uri, uri=True, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(db_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(operational_state, "get_connection", fake_get_connection)

    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")

    try:
        yield app_module.app.test_client()
    finally:
        keeper.close()
        sys.modules.pop("app", None)


def test_applying_recommendations_updates_flights_impact_and_audit(live_client):
    flights_response = live_client.get("/api/flights?limit=24")
    assert flights_response.status_code == 200
    flights_data = flights_response.get_json()
    assert flights_data["summary"]["total_flights"] == 24
    assert flights_data["summary"]["predicted_delay_minutes"] > 0

    flight_id = flights_data["flights"][0]["id"]

    detail_response = live_client.get(f"/api/flight/{flight_id}/detail")
    assert detail_response.status_code == 200
    detail_data = detail_response.get_json()
    before_flight = detail_data["flight"]
    recommendation_ids = [item["id"] for item in detail_data["recommendations"][:2]]

    assert len(recommendation_ids) == 2

    apply_response = live_client.post(
        f"/api/flight/{flight_id}/apply_recommendations",
        json={"action_ids": recommendation_ids, "operator_id": "test_operator"},
    )
    assert apply_response.status_code == 200
    apply_data = apply_response.get_json()
    after_flight = apply_data["flight"]

    assert after_flight["risk"] < before_flight["risk"]
    assert after_flight["confidence_percent"] < before_flight["confidence_percent"]
    assert after_flight["predicted_delay_minutes"] < before_flight["predicted_delay_minutes"]
    assert len(apply_data["recommendations"]) == len(detail_data["recommendations"]) - 2
    assert len(apply_data["completed_recommendations"]) == 2

    flights_after_response = live_client.get("/api/flights?limit=24")
    assert flights_after_response.status_code == 200
    flights_after_data = flights_after_response.get_json()
    flight_after = next(
        flight for flight in flights_after_data["flights"] if flight["id"] == flight_id
    )

    assert flight_after["risk"] == after_flight["risk"]
    assert flight_after["confidence_percent"] == after_flight["confidence_percent"]
    assert (
        flights_after_data["summary"]["prevented_delay_minutes"]
        == apply_data["impact_summary"]["total_time_saved"]
    )

    impact_response = live_client.get("/api/impact_summary")
    assert impact_response.status_code == 200
    impact_data = impact_response.get_json()

    assert impact_data["total_time_saved"] > 0
    assert impact_data["after_total_delay"] < impact_data["before_total_delay"]
    assert impact_data["completed_actions"] == 2

    audit_response = live_client.get("/api/audit_feed?limit=10")
    assert audit_response.status_code == 200
    audit_data = audit_response.get_json()

    assert len(audit_data["entries"]) == 1
    audit_entry = audit_data["entries"][0]
    assert audit_entry["flight_id"] == flight_id
    assert audit_entry["operator_id"] == "test_operator"
    assert audit_entry["after_risk_percent"] < audit_entry["before_risk_percent"]
    assert audit_entry["after_delay_minutes"] < audit_entry["before_delay_minutes"]
