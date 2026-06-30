import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def _artifact_path(filename):
    return os.path.join(REPO_ROOT, "models", filename)

from loaders.backend_loader_delay_predictor import load_artifact as load_delay_artifact, predict_delay
from loaders.backend_loader_maintenance_impact import load_artifact as load_maintenance_artifact, predict_maintenance_impact
from loaders.backend_loader_passenger_flow import load_artifact as load_passenger_artifact, predict_passenger_flow
from loaders.backend_loader_baggage_risk import load_artifact as load_baggage_artifact, predict_baggage_risk
from loaders.backend_loader_gate_events import load_artifact as load_gate_artifact, detect_gate_event_risks
from loaders.backend_loader_security_congestion import load_artifact as load_security_artifact, predict_security_congestion
from loaders.backend_loader_staff_resource import load_artifact as load_staff_artifact, predict_staffing_risk
from loaders.backend_loader_retail_dwell import load_artifact as load_retail_artifact, predict_retail_dwell_risk

from backend.airport_state_builder import build_airport_state


# ----------------------------
# 1. Load all artifacts once
# ----------------------------

delay_artifact = load_delay_artifact(_artifact_path("airflow_delay_predictor_artifact.pkl"))
maintenance_artifact = load_maintenance_artifact(_artifact_path("airflow_maintenance_impact_artifact.pkl"))
passenger_artifact = load_passenger_artifact(_artifact_path("airflow_passenger_flow_artifact.pkl"))
baggage_artifact = load_baggage_artifact(_artifact_path("airflow_baggage_risk_artifact.pkl"))
gate_artifact = load_gate_artifact(_artifact_path("airflow_gate_event_artifact.pkl"))
security_artifact = load_security_artifact(_artifact_path("airflow_security_congestion_artifact.pkl"))
staff_artifact = load_staff_artifact(_artifact_path("airflow_staff_resource_artifact.pkl"))
retail_artifact = load_retail_artifact(_artifact_path("airflow_retail_dwell_artifact.pkl"))


# ----------------------------
# 2. Run specialists
# ----------------------------

def run_airport_specialists(
    flight_id,
    flight_features,
    maintenance_features,
    passenger_features,
    baggage_features,
    gate_events,
    security_events,
    staff_events,
    retail_events
):

    delay_output = predict_delay(
        delay_artifact,
        flight_features
    )

    maintenance_output = predict_maintenance_impact(
        maintenance_artifact,
        maintenance_features
    )

    passenger_flow_output = predict_passenger_flow(
        passenger_artifact,
        passenger_features
    )

    baggage_output = predict_baggage_risk(
        baggage_artifact,
        baggage_features
    )

    gate_events_output = detect_gate_event_risks(
        gate_artifact,
        gate_events
    )

    security_output = predict_security_congestion(
        security_artifact,
        security_events
    )

    staffing_output = predict_staffing_risk(
        staff_artifact,
        staff_events
    )

    retail_output = predict_retail_dwell_risk(
        retail_artifact,
        retail_events
    )

    airport_state = build_airport_state(
        flight_id=flight_id,
        delay_output=delay_output,
        maintenance_output=maintenance_output,
        passenger_flow_output=passenger_flow_output,
        baggage_output=baggage_output,
        gate_events_output=gate_events_output,
        security_output=security_output,
        staffing_output=staffing_output,
        retail_output=retail_output
    )

    return airport_state
