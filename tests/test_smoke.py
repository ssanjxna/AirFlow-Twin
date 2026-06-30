import importlib

from backend.airport_state_builder import build_airport_state
from gemini_orchestrator import get_gemini_recommendation
from models.parking_predictor import ParkingCongestionPredictor
from utils.data_loader import AirportDataLoader


def test_airport_state_builder_normalizes_mixed_specialist_outputs():
    state = build_airport_state(
        flight_id="TEST-123",
        delay_output={"delay_probability": 0.87, "delay_risk_percent": 87, "risk_level": "critical"},
        maintenance_output={
            "maintenance_delay_probability": 0.62,
            "maintenance_delay_percent": 62,
            "risk_level": "high",
        },
        passenger_flow_output={"passenger_flow_risk_score": 73, "passenger_flow_risk_label": "High"},
        baggage_output={"risk_probability": 0.54, "risk_percent": 54, "risk_level": "High"},
    )

    assert state["specialist_outputs"]["delay"]["risk_percent"] == 87.0
    assert state["specialist_outputs"]["maintenance"]["risk_probability"] == 0.62
    assert state["specialist_outputs"]["passenger_flow"]["risk_level"] == "High"
    assert state["overall_risk"]["risk_percent"] > 0
    assert state["top_risk_sources"][0]["source"] == "delay"


def test_data_loader_falls_back_to_mock_flights_when_csvs_are_missing():
    loader = AirportDataLoader(data_dir="does-not-exist")

    flights = loader.get_current_flights(limit=2)

    assert len(flights) == 2
    assert all("id" in flight for flight in flights)
    assert all("risk" in flight for flight in flights)


def test_parking_predictor_can_load_and_predict():
    predictor = ParkingCongestionPredictor()
    predictor.load_model()

    prediction = predictor.predict(
        hour=9,
        day_type="weekday",
        weather="clear",
        flights_arriving=8,
        occupancy_rate=75,
        is_peak_hour=1,
    )

    assert prediction["status"] in {"low", "normal", "high", "critical"}
    assert isinstance(prediction["recommendations"], list)
    assert "congestion_score" in prediction
    assert prediction["model_version"]


def test_orchestrator_runner_imports_cleanly():
    module = importlib.import_module("backend.orchestrator_runner")

    assert hasattr(module, "run_airport_specialists")


def test_gemini_orchestrator_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    recommendation = get_gemini_recommendation(
        {
            "flight_id": "TEST-123",
            "specialist_outputs": {"delay": {"risk_probability": 0.8, "risk_percent": 80, "risk_level": "Critical"}},
            "overall_risk": {"risk_percent": 80, "risk_level": "Critical"},
        },
        api_key=None,
    )

    assert recommendation["flight_id"] == "TEST-123"
    assert recommendation["human_approval_required"] is True
