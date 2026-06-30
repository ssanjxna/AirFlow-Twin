import os
from pathlib import Path
import random
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
from dotenv import load_dotenv
from loaders.backend_loader_delay_predictor import load_artifact as load_delay_artifact
from loaders.backend_loader_delay_predictor import predict_delay
from models.parking_predictor import ParkingCongestionPredictor
from utils.data_loader import AirportDataLoader

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"


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
    flights = data_loader.get_current_flights(limit=15)
    resources = data_loader.get_resource_status()
    
    # Update risk scores with AI model
    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)
    
    return jsonify({"flights": flights, "resources": resources})

@app.route('/api/parking_status')
def get_parking_status():
    """Get current parking congestion status and predictions"""
    initialize_runtime()
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime('%A')
    day_type = 'weekend' if current_day in ['Saturday', 'Sunday'] else 'weekday'
    
    # Simulate current conditions
    current_occupancy_rate = 65
    flights_arriving = 8
    
    # Determine if peak hour
    is_peak = 1 if (7 <= current_hour <= 9) or (17 <= current_hour <= 19) else 0
    
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
        'is_peak_hour': bool(is_peak)
    })



# ============================================================================
# SOCKET.IO REAL-TIME SIMULATION
# ============================================================================

def simulation_loop():
    """Background task for real-time simulation updates"""
    initialize_runtime()

    while True:
        flights = data_loader.get_current_flights(limit=15)
        
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
