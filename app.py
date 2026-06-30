import os
from pathlib import Path
import random
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from dotenv import load_dotenv
from backend.airport_state_builder import build_airport_state
from database.operational_state import (
    apply_recommendations,
    ensure_operational_tables,
    ensure_recommendation_actions,
    get_audit_feed,
    get_flight_analysis_state,
    get_impact_summary,
    overlay_persisted_state,
    sync_flight_state,
)
from gemini_orchestrator import get_gemini_recommendation
from loaders.backend_loader_delay_predictor import load_artifact as load_delay_artifact
from loaders.backend_loader_delay_predictor import predict_delay
from models.parking_predictor import ParkingCongestionPredictor
from utils.data_loader import AirportDataLoader

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
# TRACKED_FLIGHT_LIMIT is now dynamic - computed from database at runtime
TRACKED_FLIGHT_LIMIT = None


def _log(message):
    """Use ASCII-only startup logs so Windows console imports do not fail."""
    print(message)

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")
DEBUG_MODE = os.getenv("FLASK_DEBUG", "1").strip().lower() not in {"0", "false", "no"}

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

data_loader = AirportDataLoader(str(DATA_DIR))
parking_predictor = ParkingCongestionPredictor()
client = None
GEMINI_AVAILABLE = False
delay_artifact = None
runtime_initialized = False


def _is_werkzeug_reloader_parent():
    return __name__ == '__main__' and DEBUG_MODE and os.environ.get('WERKZEUG_RUN_MAIN') != 'true'


def initialize_runtime():
    global GEMINI_AVAILABLE, client, delay_artifact, runtime_initialized

    if runtime_initialized:
        return

    ensure_operational_tables()

    try:
        import google.generativeai as genai
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            client = genai.GenerativeModel("gemini-2.5-flash")
            GEMINI_AVAILABLE = True
            _log("Gemini API configured successfully.")
        else:
            client = None
            GEMINI_AVAILABLE = False
            _log("WARNING: GEMINI_API_KEY not found in .env file")
    except Exception as exc:
        client = None
        GEMINI_AVAILABLE = False
        _log(f"WARNING: Gemini API not available: {exc}")

    data_loader.load_all_datasets()
    _log("Airport data loaded successfully.")

    try:
        delay_artifact = load_delay_artifact(MODELS_DIR / "airflow_delay_predictor_artifact.pkl")
        _log("Delay predictor artifact loaded successfully.")
    except Exception as exc:
        delay_artifact = None
        _log(f"WARNING: Could not load delay artifact: {exc}")

    try:
        parking_predictor.load_model()
        _log("Parking congestion predictor loaded successfully.")
    except Exception as exc:
        _log(f"WARNING: Could not load parking artifact: {exc}")

    runtime_initialized = True


def get_dynamic_flight_limit():
    """Get the current number of flights in the database"""
    return max(1, data_loader.get_total_flights_count())


if not _is_werkzeug_reloader_parent():
    initialize_runtime()

# Global state for real-time simulation
airport_state = {
    "current_time": "09:00",
    "flights": [],
    "resources": {}
}
simulation_task = None

# ============================================================================
# AI HELPER FUNCTIONS
# ============================================================================

def _build_delay_artifact_features(flight):
    day_of_week = str(flight.get("day_of_week", "Mon"))
    scheduled_departure = str(flight.get("scheduled_departure", "10:00"))

    try:
        departure_hour = int(scheduled_departure.split(":")[0])
    except (TypeError, ValueError, IndexError):
        departure_hour = 10

    now = datetime.now()
    origin = str(flight.get("origin", "DEL"))
    destination = str(flight.get("destination", "SIN"))
    gate = str(flight.get("gate", "T1"))
    distance = int(flight.get("distance", 1000))
    is_weekend = int(day_of_week.lower().startswith(("sat", "sun")))
    is_peak_hour = int((7 <= departure_hour <= 9) or (17 <= departure_hour <= 19))
    scheduled_duration = max(45, int(distance / 700 * 60))

    return {
        "airline_code": str(flight.get("airline_code", "UK")),
        "origin": origin,
        "destination": destination,
        "route": f"{origin}-{destination}",
        "aircraft_type": str(flight.get("aircraft_type", "A320")),
        "terminal": gate[:2] if gate else "T1",
        "gate": gate,
        "is_international": 1,
        "distance": distance,
        "passenger_count": int(flight.get("passenger_count", 180)),
        "maintenance_required": int(flight.get("maintenance_required", 0)),
        "fuel_level": int(flight.get("fuel_level", 75)),
        "baggage_count": int(flight.get("baggage_count", 120)),
        "load_factor": float(flight.get("load_factor", 0.8)),
        "time_of_day": str(flight.get("time_of_day", "Morning")),
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "season": str(flight.get("season", "Summer")),
        "flight_type": str(flight.get("flight_type", "Passenger")),
        "departure_hour": departure_hour,
        "departure_month": int(flight.get("departure_month", now.month)),
        "departure_day": int(flight.get("departure_day", now.day)),
        "arrival_hour": int(flight.get("arrival_hour", (departure_hour + 2) % 24)),
        "is_peak_hour": is_peak_hour,
        "scheduled_duration": int(flight.get("scheduled_duration", scheduled_duration)),
    }


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _risk_level_from_percent(percent):
    percent = float(percent)

    if percent >= 80:
        return "Critical"
    if percent >= 50:
        return "High"
    if percent >= 25:
        return "Medium"
    return "Low"


def _predict_delay_for_flight(flight):
    base_risk = float(flight.get("risk", 50))

    if delay_artifact is None:
        risk_percent = round(base_risk, 2)
        probability = round(min(0.99, max(0.05, risk_percent / 100)), 4)
        predicted_delay_minutes = max(_safe_int(flight.get("delay_minutes"), 0), int(round(risk_percent * 0.5)))

        return {
            "prediction": "Delayed" if risk_percent >= 50 else "On-Time",
            "delay_probability": probability,
            "risk_probability": probability,
            "risk_percent": risk_percent,
            "risk_level": _risk_level_from_percent(risk_percent),
            "predicted_delay_minutes": predicted_delay_minutes,
            "model_version": "fallback_delay_estimator",
        }

    prediction = predict_delay(delay_artifact, _build_delay_artifact_features(flight))
    risk_percent = round(float(prediction["risk_percent"]), 2)
    predicted_delay_minutes = max(_safe_int(flight.get("delay_minutes"), 0), int(round(risk_percent * 0.5)))

    return {
        **prediction,
        "predicted_delay_minutes": predicted_delay_minutes,
    }


def _match_count(df, column_index, value):
    if df is None:
        return 0

    series = df.iloc[:, column_index].astype(str)
    return int((series == str(value)).sum())


def _build_operational_context(flight, delay_prediction):
    flight_id = flight["id"]
    gate = flight.get("gate", "A1")
    delay_reason = str(flight.get("delay_reason", "Operational")).upper()

    passenger_count = max(
        _safe_int(flight.get("passenger_count"), 0),
        _match_count(data_loader.passengers_df, 10, flight_id)
    )
    maintenance_count = _match_count(data_loader.maintenance_df, 2, flight_id)
    gate_event_count = _match_count(data_loader.gate_events_df, 1, flight_id)
    same_gate_load = _match_count(data_loader.gate_events_df, 2, gate)

    departure_hour = _safe_int(str(flight.get("scheduled_departure", "10:00")).split(":")[0], 10)
    is_peak = int((7 <= departure_hour <= 9) or (17 <= departure_hour <= 19))

    maintenance_risk = min(100.0, 15 + maintenance_count * 18 + flight.get("maintenance_required", 0) * 25 + (20 if delay_reason in {"TECH", "MTC", "MAINTENANCE"} else 0))
    passenger_risk = min(100.0, 18 + passenger_count * 0.18 + is_peak * 10 + max(delay_prediction["predicted_delay_minutes"] - 15, 0) * 0.2)
    baggage_risk = min(100.0, 12 + _safe_int(flight.get("baggage_count"), 0) * 0.12 + abs(_safe_int(flight.get("delay_minutes"), 0)) * 0.35)
    gate_risk = min(100.0, 10 + gate_event_count * 10 + same_gate_load * 2 + is_peak * 10)
    security_risk = min(100.0, passenger_risk * 0.78 + is_peak * 8)
    staffing_risk = min(100.0, gate_risk * 0.55 + maintenance_risk * 0.25 + is_peak * 10)
    retail_risk = min(100.0, passenger_risk * 0.45 + (5 if "LONG" in str(flight.get("flight_type", "")).upper() else 0))

    airport_state = build_airport_state(
        flight_id=flight_id,
        delay_output=delay_prediction,
        maintenance_output={
            "risk_probability": round(maintenance_risk / 100, 4),
            "risk_percent": round(maintenance_risk, 2),
            "risk_level": _risk_level_from_percent(maintenance_risk),
        },
        passenger_flow_output={
            "risk_probability": round(passenger_risk / 100, 4),
            "risk_percent": round(passenger_risk, 2),
            "risk_level": _risk_level_from_percent(passenger_risk),
        },
        baggage_output={
            "risk_probability": round(baggage_risk / 100, 4),
            "risk_percent": round(baggage_risk, 2),
            "risk_level": _risk_level_from_percent(baggage_risk),
        },
        gate_events_output={
            "risk_probability": round(gate_risk / 100, 4),
            "risk_percent": round(gate_risk, 2),
            "risk_level": _risk_level_from_percent(gate_risk),
        },
        security_output={
            "risk_probability": round(security_risk / 100, 4),
            "risk_percent": round(security_risk, 2),
            "risk_level": _risk_level_from_percent(security_risk),
        },
        staffing_output={
            "risk_probability": round(staffing_risk / 100, 4),
            "risk_percent": round(staffing_risk, 2),
            "risk_level": _risk_level_from_percent(staffing_risk),
        },
        retail_output={
            "risk_probability": round(retail_risk / 100, 4),
            "risk_percent": round(retail_risk, 2),
            "risk_level": _risk_level_from_percent(retail_risk),
        },
    )

    context = {
        "passenger_count": passenger_count,
        "maintenance_count": maintenance_count,
        "gate_event_count": gate_event_count,
        "same_gate_load": same_gate_load,
        "is_peak": is_peak,
        "delay_reason": delay_reason,
    }

    return airport_state, context


def _build_risk_cause(flight, delay_prediction, airport_state, context):
    causes = []

    if context["maintenance_count"] or flight.get("maintenance_required"):
        causes.append(
            f"Maintenance signals are elevated with {context['maintenance_count']} linked engineering record(s) and delay reason {flight.get('delay_reason', 'Operational')}."
        )

    if context["gate_event_count"] or context["same_gate_load"] >= 3:
        causes.append(
            f"Gate {flight.get('gate', 'A1')} is under pressure with {context['same_gate_load']} related gate events in the current operational window."
        )

    if context["passenger_count"] >= 160:
        causes.append(
            f"Passenger volume is high at about {context['passenger_count']} travelers, increasing turnaround and boarding coordination risk."
        )

    if delay_prediction["predicted_delay_minutes"] >= 30:
        causes.append(
            f"The delay model is projecting roughly {delay_prediction['predicted_delay_minutes']} minutes of disruption based on the current flight profile."
        )

    if not causes:
        causes.append(
            f"Operational risk is being driven by a combination of departure timing, gate activity, and current turnaround constraints."
        )

    return " ".join(causes[:3])


def _serialize_recommendations(recommendation, airport_state):
    actions = recommendation.get("recommended_actions", [])
    expected_impact = recommendation.get("expected_impact", {})
    current_risk = float(expected_impact.get("current_overall_risk_percent", airport_state["overall_risk"]["risk_percent"]))
    target_risk = float(expected_impact.get("estimated_risk_after_actions_percent", current_risk))
    total_risk_reduction = max(0.0, current_risk - target_risk)
    total_delay_reduction = max(0, _safe_int(expected_impact.get("estimated_delay_reduction_minutes"), 0))
    fallback_delay_share = max(4, int(round(total_delay_reduction / max(len(actions), 1)))) if total_delay_reduction else 6

    cards = []
    for index, action in enumerate(actions, start=1):
        delay_reduction = max(1, _safe_int(action.get("expected_delay_reduction_minutes"), fallback_delay_share))
        share = (delay_reduction / total_delay_reduction) if total_delay_reduction else (1 / max(len(actions), 1))
        risk_reduction = max(5, int(round(total_risk_reduction * share))) if total_risk_reduction else 8
        cards.append({
            "id": f"rec-{index}",
            "text": action.get("action", "Review operational mitigation"),
            "impact": f"-{delay_reduction}m delay, -{risk_reduction}% risk",
            "delay_reduction": delay_reduction,
            "risk_reduction": risk_reduction,
            "target_team": action.get("target_team", "Operations"),
            "priority": action.get("priority", recommendation.get("overall_priority", "High")),
            "validation_required": bool(action.get("validation_required", True)),
        })

    return cards


def _enrich_flight(flight):
    delay_prediction = _predict_delay_for_flight(flight)
    enriched = {
        **flight,
        "risk": int(round(float(delay_prediction["risk_percent"]))),
        "risk_level": delay_prediction.get("risk_level", _risk_level_from_percent(delay_prediction["risk_percent"])),
        "confidence_percent": int(round(float(delay_prediction.get("delay_probability", delay_prediction.get("risk_probability", 0.5))) * 100)),
        "predicted_delay_minutes": int(delay_prediction["predicted_delay_minutes"]),
        "delay_prediction": delay_prediction.get("prediction", "Delayed"),
    }
    return enriched, delay_prediction


def _summarize_flights(flights):
    high_risk_count = sum(1 for flight in flights if flight["risk"] >= 80)
    total_predicted_delay_minutes = sum(_safe_int(flight.get("predicted_delay_minutes"), 0) for flight in flights)
    impact_summary = get_impact_summary()
    prevented_delay_minutes = impact_summary["total_time_saved"]

    return {
        "high_risk_count": high_risk_count,
        "total_flights": len(flights),
        "predicted_delay_minutes": total_predicted_delay_minutes,
        "prevented_delay_minutes": prevented_delay_minutes,
        "average_risk": round(sum(flight["risk"] for flight in flights) / max(len(flights), 1), 1),
    }


def get_ai_risk_score(flight):
    global delay_artifact

    initialize_runtime()

    if delay_artifact is None:
        return flight.get('risk', 50)

    try:
        prediction = predict_delay(delay_artifact, _build_delay_artifact_features(flight))
        return int(prediction["risk_percent"])
    except Exception as exc:
        _log(f"Delay artifact prediction error: {exc}")
        delay_artifact = None
        return flight.get('risk', 50)

def generate_ai_recommendation(flight):
    initialize_runtime()

    if not GEMINI_AVAILABLE or client is None:
        return "<div class='text-slate-400'>AI Recommendations unavailable (API Key missing).</div>"
    try:
        prompt = f"Flight {flight['id']} has a {flight['risk']}% delay risk. Give 3 short operational recommendations as bullet points."
        response = client.generate_content(prompt)
        return response.text
    except Exception:
        return "<div class='text-slate-400'>Error generating recommendations.</div>"

# ============================================================================
# FLASK ROUTES - PAGE ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/flights')
def flights_page():
    """All flights page"""
    return render_template('flights.html')

@app.route('/horizon')
def horizon_page():
    """Prediction horizon page"""
    return render_template('horizon.html')

@app.route('/flight/<flight_id>')
def flight_detail(flight_id):
    """Flight detail page"""
    return render_template('flight_detail.html', flight_id=flight_id)

@app.route('/event/<int:event_index>')
def event_detail(event_index):
    """Event detail page"""
    return render_template('event_detail.html', event_index=event_index)

@app.route('/parking')
def parking_detail():
    """Parking detail page"""
    return render_template('parking_detail.html')

@app.route('/ai-impact')
def ai_impact_page():
    """AI Impact Analysis page"""
    return render_template('ai_impact.html')

@app.route('/audit')
def audit_page():
    """Audit Log page (placeholder)"""
    return render_template('audit.html')

@app.route('/calibrate')
def calibrate():
    return render_template('calibrate.html')

# ============================================================================
# FLASK ROUTES - API ENDPOINTS
# ============================================================================

@app.route('/api/flights')
def get_flights():
    """Get current flight data with AI-calculated risk scores"""
    initialize_runtime()
    # Get all flights from database by default (no limit)
    limit = request.args.get('limit', default=None, type=int)
    if limit is None:
        limit = get_dynamic_flight_limit()
    else:
        limit = max(1, min(limit, 1000))  # Cap at 1000 max

    flights = data_loader.get_current_flights(limit=limit)
    resources = data_loader.get_resource_status()
    enriched_flights = []

    for flight in flights:
        enriched, _ = _enrich_flight(flight)
        sync_flight_state(enriched)
        enriched = overlay_persisted_state(enriched)
        enriched_flights.append(enriched)

    return jsonify({
        "flights": enriched_flights,
        "resources": resources,
        "summary": _summarize_flights(enriched_flights),
    })


@app.route('/api/flight/<flight_id>/detail')
def get_flight_detail_data(flight_id):
    initialize_runtime()

    flight = data_loader.get_flight_by_id(flight_id)
    if flight is None:
        return jsonify({"error": f"Flight {flight_id} not found"}), 404

    enriched_flight, delay_prediction = _enrich_flight(flight)
    airport_state, context = _build_operational_context(enriched_flight, delay_prediction)
    recommendation = get_gemini_recommendation(airport_state, api_key=os.getenv('GEMINI_API_KEY'))
    risk_cause = _build_risk_cause(enriched_flight, delay_prediction, airport_state, context)
    executive_summary = recommendation.get("executive_summary", "")

    sync_flight_state(
        enriched_flight,
        risk_cause=risk_cause,
        executive_summary=executive_summary,
        airport_state=airport_state,
        recommendation=recommendation,
    )
    enriched_flight = overlay_persisted_state(enriched_flight)
    recommendation_cards = _serialize_recommendations(recommendation, airport_state)
    ensure_recommendation_actions(flight_id, recommendation_cards)
    analysis_state = get_flight_analysis_state(flight_id)

    if analysis_state is None:
        return jsonify({"error": f"Unable to load persisted analysis for {flight_id}"}), 500

    state_row = analysis_state["state"]
    executive_summary = state_row.get("executive_summary") or executive_summary

    return jsonify({
        "flight": enriched_flight,
        "airport_state": airport_state,
        "recommendation": recommendation,
        "risk_cause": state_row.get("risk_cause") or risk_cause,
        "recommendations": analysis_state["open_recommendations"],
        "completed_recommendations": analysis_state["completed_recommendations"],
        "expected_impact": analysis_state["expected_impact"],
        "executive_summary": executive_summary,
    })


@app.route('/api/flight/<flight_id>/apply_recommendations', methods=['POST'])
def apply_flight_recommendations(flight_id):
    initialize_runtime()
    payload = request.get_json(silent=True) or {}
    action_ids = payload.get("action_ids") or []
    operator_id = str(payload.get("operator_id") or "dashboard_user")

    try:
        result = apply_recommendations(flight_id, action_ids, operator_id=operator_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    flight = data_loader.get_flight_by_id(flight_id)
    if flight is None:
        return jsonify({"error": f"Flight {flight_id} not found"}), 404

    enriched_flight, delay_prediction = _enrich_flight(flight)
    enriched_flight = overlay_persisted_state(enriched_flight)
    airport_state, context = _build_operational_context(enriched_flight, delay_prediction)
    risk_cause = _build_risk_cause(enriched_flight, delay_prediction, airport_state, context)
    analysis_state = get_flight_analysis_state(flight_id)

    return jsonify({
        "flight": enriched_flight,
        "risk_cause": risk_cause,
        "recommendations": analysis_state["open_recommendations"] if analysis_state else [],
        "completed_recommendations": analysis_state["completed_recommendations"] if analysis_state else [],
        "expected_impact": analysis_state["expected_impact"] if analysis_state else {},
        "applied_actions": result["applied_actions"],
        "impact_summary": get_impact_summary(),
    })


@app.route('/api/impact_summary')
def get_impact_summary_data():
    initialize_runtime()
    tracked_flights = data_loader.get_current_flights(limit=get_dynamic_flight_limit())
    for flight in tracked_flights:
        enriched, _ = _enrich_flight(flight)
        sync_flight_state(enriched)
    return jsonify(get_impact_summary())


@app.route('/api/audit_feed')
def get_audit_feed_data():
    initialize_runtime()
    limit = request.args.get('limit', default=50, type=int)
    return jsonify({
        "entries": get_audit_feed(limit=max(1, min(limit, 200))),
        "impact_summary": get_impact_summary(),
    })

@app.route('/api/parking_status')
def get_parking_status():
    """Get current parking congestion status and predictions"""
    initialize_runtime()
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime('%A')
    day_type = 'weekend' if current_day in ['Saturday', 'Sunday'] else 'weekday'
    tracked_flights = data_loader.get_current_flights(limit=get_dynamic_flight_limit())
    average_delay = round(
        sum(_safe_int(flight.get('delay_minutes'), 0) for flight in tracked_flights) / max(len(tracked_flights), 1),
        1,
    )
    flights_arriving = max(3, min(18, len(tracked_flights) // 3 + (2 if current_day in ['Friday', 'Saturday', 'Sunday'] else 0)))
    
    # Determine if peak hour
    is_peak = 1 if (7 <= current_hour <= 9) or (17 <= current_hour <= 19) else 0
    current_occupancy_rate = max(28, min(96, int(32 + flights_arriving * 3 + average_delay * 0.6 + is_peak * 12)))
    
    prediction = parking_predictor.predict(
        hour=current_hour,
        day_type=day_type,
        weather='clear',
        flights_arriving=flights_arriving,
        occupancy_rate=current_occupancy_rate,
        is_peak_hour=is_peak
    )
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'current_occupancy_rate': current_occupancy_rate,
        'congestion_score': prediction['congestion_score'],
        'status': prediction['status'],
        'color': prediction['color'],
        'recommendations': prediction['recommendations'],
        'flights_arriving': flights_arriving,
        'is_peak_hour': bool(is_peak),
        'estimated_delay_minutes': max(4, int(round(prediction['congestion_score'] * 0.22))),
        'cause': f"{flights_arriving} arriving flights, average delay of {average_delay} minutes, and {current_occupancy_rate}% occupancy are driving current parking pressure.",
    })


@app.route('/api/simulator/add-flight', methods=['POST'])
def add_flight():
    """Add a new flight to the database for simulation"""
    initialize_runtime()
    
    payload = request.get_json(silent=True) or {}
    
    # Required fields
    flight_id = payload.get('flight_id') or payload.get('id')
    flight_number = payload.get('flight_number', f"FL{random.randint(100, 9999)}")
    airline = payload.get('airline', 'Unknown')
    origin = payload.get('origin', 'DEL')
    destination = payload.get('destination', 'DXB')
    status = payload.get('status', 'scheduled')
    gate_id = payload.get('gate', 'G1')
    aircraft_type = payload.get('aircraft_type', 'Boeing 777')
    delay_minutes = int(payload.get('delay_minutes', 0))
    
    # Timestamps
    scheduled_departure = payload.get('scheduled_departure') or datetime.now().isoformat()
    scheduled_arrival = payload.get('scheduled_arrival') or (datetime.now() + timedelta(hours=4)).isoformat()
    
    if not flight_id:
        return jsonify({"error": "flight_id is required"}), 400
    
    try:
        from database.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if flight already exists
        cursor.execute("SELECT flight_id FROM flights WHERE flight_id = ?", (flight_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing flight
            cursor.execute("""
                UPDATE flights 
                SET flight_number=?, airline=?, origin=?, destination=?, 
                    scheduled_departure=?, scheduled_arrival=?, gate_id=?, 
                    status=?, aircraft_type=?, delay_minutes=?
                WHERE flight_id=?
            """, (
                flight_number, airline, origin, destination,
                scheduled_departure, scheduled_arrival, gate_id, 
                status, aircraft_type, delay_minutes, flight_id
            ))
            conn.commit()
            conn.close()
            return jsonify({
                "success": True,
                "message": f"Flight {flight_id} updated",
                "flight": {
                    "id": flight_id,
                    "flight_number": flight_number,
                    "status": status
                }
            }), 200
        else:
            # Insert new flight
            cursor.execute("""
                INSERT INTO flights 
                (flight_id, flight_number, airline, origin, destination, 
                 scheduled_departure, scheduled_arrival, gate_id, status, aircraft_type, delay_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight_id, flight_number, airline, origin, destination,
                scheduled_departure, scheduled_arrival, gate_id, status, aircraft_type, delay_minutes
            ))
            conn.commit()
            conn.close()
            return jsonify({
                "success": True,
                "message": f"Flight {flight_id} added successfully",
                "flight": {
                    "id": flight_id,
                    "flight_number": flight_number,
                    "airline": airline,
                    "origin": origin,
                    "destination": destination,
                    "gate": gate_id,
                    "status": status,
                    "delay_minutes": delay_minutes
                }
            }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SOCKET.IO REAL-TIME SIMULATION
# ============================================================================

def simulation_loop():
    """Background task for real-time simulation updates"""
    initialize_runtime()

    while True:
        flights = data_loader.get_current_flights(limit=get_dynamic_flight_limit())
        
        # Add random fluctuations to risk scores
        for flight in flights:
            base_risk = get_ai_risk_score(flight)
            fluctuation = random.randint(-3, 3)
            flight["risk"] = max(0, min(100, base_risk + fluctuation))
        
        airport_state["flights"] = flights
        airport_state["resources"] = data_loader.get_resource_status()
        
        # Emit update to all connected clients
        socketio.emit('update_map', airport_state)
        socketio.sleep(3)

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    global simulation_task

    initialize_runtime()
    _log("Client connected")

    # Keep a single simulation loop alive even if multiple clients connect.
    if simulation_task is None:
        simulation_task = socketio.start_background_task(simulation_loop)



# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    if not _is_werkzeug_reloader_parent():
        print("\n" + "="*60)
        print("AIRFLOW TWIN - AI Airport Operations Digital Twin")
        print("="*60)
        print("Starting server on http://127.0.0.1:5000")
        print("="*60 + "\n")
    
    socketio.run(app, debug=DEBUG_MODE, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5000)
