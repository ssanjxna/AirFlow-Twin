import os
import time
import random
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Gemini API
try:
    from google import genai
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        client = genai.Client(api_key=gemini_api_key)
        GEMINI_AVAILABLE = True
        print("✓ Gemini API configured successfully.")
    else:
        GEMINI_AVAILABLE = False
        print("⚠ WARNING: GEMINI_API_KEY not found in .env file")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"⚠ Gemini API not available: {e}")

# ============================================================================
# NEW MODEL LOADER IMPORTS
# ============================================================================

from loaders.backend_loader_delay_predictor import load_artifact as load_delay_artifact, predict_delay
from loaders.backend_loader_congestion_predictor import load_artifact as load_congestion_artifact, predict_congestion
from loaders.backend_loader_baggage_risk import load_artifact as load_baggage_artifact, predict_baggage_risk
from loaders.backend_loader_gate_events import load_artifact as load_gate_artifact, detect_gate_event_risks
from loaders.backend_loader_maintenance_impact import load_artifact as load_maintenance_artifact, predict_maintenance_impact
from loaders.backend_loader_passenger_flow import load_artifact as load_flow_artifact, predict_passenger_flow
from loaders.backend_loader_security_congestion import load_artifact as load_security_artifact, predict_security_congestion
from loaders.backend_loader_staff_resource import load_artifact as load_staff_artifact, predict_staffing_risk
from loaders.backend_loader_retail_dwell import load_artifact as load_retail_artifact, predict_retail_dwell_risk

# ============================================================================
# INITIALIZE DATA LOADER
# ============================================================================

from utils.data_loader import AirportDataLoader
data_loader = AirportDataLoader('data')
data_loader.load_all_datasets()
print("✓ Airport data loaded successfully.")

# ============================================================================
# LOAD ALL ML MODELS
# ============================================================================

try:
    # Core models (always load these)
    delay_model = load_delay_artifact('models/delay_predictor.pkl')
    congestion_model = load_congestion_artifact('models/parking_predictor.pkl')
    
    # New models (only load if .pkl files exist)
    baggage_model = load_baggage_artifact('models/baggage_risk.pkl') if os.path.exists('models/baggage_risk.pkl') else None
    gate_model = load_gate_artifact('models/gate_events.pkl') if os.path.exists('models/gate_events.pkl') else None
    maintenance_model = load_maintenance_artifact('models/maintenance_impact.pkl') if os.path.exists('models/maintenance_impact.pkl') else None
    flow_model = load_flow_artifact('models/passenger_flow.pkl') if os.path.exists('models/passenger_flow.pkl') else None
    security_model = load_security_artifact('models/security_congestion.pkl') if os.path.exists('models/security_congestion.pkl') else None
    staff_model = load_staff_artifact('models/staff_resource.pkl') if os.path.exists('models/staff_resource.pkl') else None
    retail_model = load_retail_artifact('models/retail_dwell.pkl') if os.path.exists('models/retail_dwell.pkl') else None
    
    print("✓ All ML models loaded successfully")
    print(f"  - Delay Model: {'✓' if delay_model else '✗'}")
    print(f"  - Congestion Model: {'✓' if congestion_model else '✗'}")
    print(f"  - Baggage Model: {'✓' if baggage_model else '✗'}")
    print(f"  - Gate Events Model: {'✓' if gate_model else '✗'}")
    print(f"  - Maintenance Model: {'✓' if maintenance_model else '✗'}")
    print(f"  - Passenger Flow Model: {'✓' if flow_model else '✗'}")
    print(f"  - Security Model: {'✓' if security_model else '✗'}")
    print(f"  - Staff Model: {'✓' if staff_model else '✗'}")
    print(f"  - Retail Model: {'✓' if retail_model else '✗'}")
    
except Exception as e:
    print(f"⚠ Warning: Some models could not be loaded: {e}")
    delay_model = None
    congestion_model = None
    baggage_model = None
    gate_model = None
    maintenance_model = None
    flow_model = None
    security_model = None
    staff_model = None
    retail_model = None

# Global state for real-time simulation
airport_state = {
    "current_time": "09:00",
    "flights": [],
    "resources": {}
}

# ============================================================================
# AI HELPER FUNCTIONS
# ============================================================================

def get_ai_risk_score(flight):
    """Get AI-calculated risk score using the new delay predictor model"""
    if delay_model is None:
        return flight.get('risk', 50)
    
    try:
        # Prepare flight data for the model
        flight_data = {
            'origin': flight.get('origin', 'DEL'),
            'destination': flight.get('destination', 'SIN'),
            'airline_code': flight.get('airline_code', 'UK'),
            'distance': flight.get('distance', 1000),
            'time_of_day': flight.get('time_of_day', 'Morning'),
            'day_of_week': flight.get('day_of_week', 'Mon')
        }
        
        # Get prediction from model
        prediction = predict_delay(delay_model, flight_data)
        return prediction['delay_risk_percent']
    except Exception as e:
        print(f"Error predicting delay for {flight.get('id', 'unknown')}: {e}")
        return flight.get('risk', 50)

def generate_ai_recommendation(flight):
    """Generate AI recommendations using Gemini API"""
    if not GEMINI_AVAILABLE:
        return "<div class='text-slate-400'>AI Recommendations unavailable (API Key missing).</div>"
    try:
        prompt = f"Flight {flight['id']} has a {flight['risk']}% delay risk. Give 3 short operational recommendations as bullet points."
        response = client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt)
        return response.text
    except Exception as e:
        return "<div class='text-slate-400'>Error generating recommendations.</div>"


def get_parking_prediction_payload():
    """Return current parking congestion prediction payload and recommendations."""
    if not congestion_model:
        return {
            'timestamp': datetime.now().isoformat(),
            'current_occupancy_rate': 65,
            'congestion_score': 65,
            'status': 'Medium',
            'color': 'yellow',
            'recommendations': [
                {'id': 'parking-rec-1', 'text': 'Activate overflow parking guidance', 'impact': '-15% congestion', 'riskReduction': 15, 'delayReduction': 8},
                {'id': 'parking-rec-2', 'text': 'Reassign staff to curbside operations', 'impact': '-10% congestion', 'riskReduction': 10, 'delayReduction': 5}
            ],
            'flights_arriving': 8,
            'is_peak_hour': False,
            'error': 'Congestion model not loaded'
        }

    try:
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime('%A')
        day_type = 'weekend' if current_day in ['Saturday', 'Sunday'] else 'weekday'

        current_occupancy_rate = 65
        flights_arriving = 8
        is_peak = 1 if (7 <= current_hour <= 9) or (17 <= current_hour <= 19) else 0

        airport_data = {
            'hour': current_hour,
            'day_type': day_type,
            'weather': 'clear',
            'flights_arriving': flights_arriving,
            'occupancy_rate': current_occupancy_rate,
            'is_peak_hour': is_peak
        }

        prediction = predict_congestion(congestion_model, airport_data)
        congestion_level = prediction['congestion_level']
        if congestion_level == 'High':
            color = 'red'
            status = 'Critical'
            recommendations = [
                {'id': 'parking-rec-1', 'text': 'Open overflow parking P3 and P4', 'impact': '-30% congestion', 'riskReduction': 30, 'delayReduction': 15},
                {'id': 'parking-rec-2', 'text': 'Activate dynamic signage and shuttle support', 'impact': '-20% congestion', 'riskReduction': 20, 'delayReduction': 10}
            ]
        elif congestion_level == 'Medium':
            color = 'yellow'
            status = 'Medium'
            recommendations = [
                {'id': 'parking-rec-1', 'text': 'Shift staff to curbside guidance', 'impact': '-15% congestion', 'riskReduction': 15, 'delayReduction': 8},
                {'id': 'parking-rec-2', 'text': 'Open temporary overflow lanes', 'impact': '-10% congestion', 'riskReduction': 10, 'delayReduction': 5}
            ]
        else:
            color = 'green'
            status = 'Low'
            recommendations = [
                {'id': 'parking-rec-1', 'text': 'Maintain normal circulation and monitor throughput', 'impact': '-5% congestion', 'riskReduction': 5, 'delayReduction': 3}
            ]

        return {
            'timestamp': datetime.now().isoformat(),
            'current_occupancy_rate': current_occupancy_rate,
            'congestion_score': prediction['probabilities']['High'],
            'status': status,
            'color': color,
            'recommendations': recommendations,
            'flights_arriving': flights_arriving,
            'is_peak_hour': bool(is_peak),
            'model_prediction': prediction
        }

    except Exception as e:
        print(f"Error predicting congestion: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'current_occupancy_rate': 65,
            'congestion_score': 65,
            'status': 'Medium',
            'color': 'yellow',
            'recommendations': [],
            'flights_arriving': 8,
            'is_peak_hour': False,
            'error': str(e)
        }


def build_live_events(time_horizon=0, flights=None):
    """Build live prediction events from backend models for the frontend."""
    if flights is None:
        flights = data_loader.get_current_flights(limit=10)

    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)

    parking_payload = get_parking_prediction_payload()
    events = []

    for flight in sorted(flights, key=lambda item: item.get('risk', 0), reverse=True)[:4]:
        risk_score = int(round(flight.get('risk', 0)))
        if risk_score < 50:
            continue

        events.append({
            'id': f"flight-{flight['id']}",
            'type': 'delay',
            'time': f'+{time_horizon if time_horizon else 0}m',
            'text': f"{flight['id']} shows {risk_score}% delay risk",
            'impact': f"Potential {max(10, int(risk_score / 6))}m knock-on delay",
            'risk': risk_score,
            'flight_id': flight['id'],
            'recommendations': [
                {'id': f"rec-{flight['id']}-1", 'text': 'Reassign gate and boarding support', 'impact': '-8m delay', 'riskReduction': 8, 'delayReduction': 8},
                {'id': f"rec-{flight['id']}-2", 'text': 'Open standby maintenance crew pool', 'impact': '-5m delay', 'riskReduction': 5, 'delayReduction': 5}
            ]
        })

    if parking_payload.get('congestion_score', 0) >= 55:
        events.append({
            'id': 'parking-event',
            'type': 'parking',
            'time': f'+{time_horizon if time_horizon else 0}m',
            'text': 'Parking congestion is trending above threshold',
            'impact': 'Ground vehicles may slow arrivals and curbside flow',
            'risk': int(round(parking_payload.get('congestion_score', 0))),
            'flight_id': 'PARKING',
            'recommendations': parking_payload.get('recommendations', [])
        })

    if not events:
        events.append({
            'id': 'stable-ops',
            'type': 'stability',
            'time': f'+{time_horizon if time_horizon else 0}m',
            'text': 'Operations remain stable with no critical hotspots',
            'impact': 'Current staffing levels are sufficient for the next window',
            'risk': 25,
            'flight_id': None,
            'recommendations': []
        })

    return {
        'events': events,
        'message': f"Prediction for +{time_horizon}m",
        'modifiers': {
            'parking_score': parking_payload.get('congestion_score', 0),
            'high_risk_flights': len([f for f in flights if f.get('risk', 0) >= 70])
        },
        'newFlights': [flight['id'] for flight in flights[:3]]
    }

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
    """Calibration tool page"""
    return render_template('calibrate.html')

# ============================================================================
# FLASK ROUTES - API ENDPOINTS
# ============================================================================

@app.route('/api/flights')
def get_flights():
    """Get current flight data with AI-calculated risk scores"""
    flights = data_loader.get_current_flights(limit=15)
    resources = data_loader.get_resource_status()
    
    # Update risk scores with AI model
    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)
    
    return jsonify({"flights": flights, "resources": resources})

@app.route('/api/parking_status')
def get_parking_status():
    """Get current parking congestion status and predictions"""
    return jsonify(get_parking_prediction_payload())


@app.route('/api/operations-summary')
def get_operations_summary():
    """Return summary metrics used by the dashboard header cards."""
    flights = data_loader.get_current_flights(limit=15)
    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)

    parking_payload = get_parking_prediction_payload()
    high_risk_count = sum(1 for flight in flights if flight.get('risk', 0) >= 70)
    predicted_delay_total = int(sum(max(0, min(100, flight.get('risk', 0))) * 0.35 for flight in flights) / 5)

    return jsonify({
        'high_risk_count': high_risk_count,
        'predicted_delay_total_minutes': predicted_delay_total,
        'prevented_delay_minutes': max(0, min(90, predicted_delay_total // 2)),
        'parking_score': parking_payload.get('congestion_score', 0),
        'parking_status': parking_payload.get('status', 'Medium')
    })

# ============================================================================
# NEW PREDICTION ENDPOINTS
# ============================================================================

@app.route('/api/predict/baggage', methods=['POST'])
def predict_baggage_endpoint():
    """Predict baggage handling risk"""
    if not baggage_model:
        return jsonify({"error": "Baggage model not loaded"}), 503
    
    try:
        data = request.json
        result = predict_baggage_risk(baggage_model, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/gate-events', methods=['POST'])
def predict_gate_events_endpoint():
    """Detect gate event risks"""
    if not gate_model:
        return jsonify({"error": "Gate events model not loaded"}), 503
    
    try:
        data = request.json
        events = data.get('events', [])
        result = detect_gate_event_risks(gate_model, events)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/maintenance', methods=['POST'])
def predict_maintenance_endpoint():
    """Predict maintenance impact"""
    if not maintenance_model:
        return jsonify({"error": "Maintenance model not loaded"}), 503
    
    try:
        data = request.json
        result = predict_maintenance_impact(maintenance_model, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/passenger-flow', methods=['POST'])
def predict_passenger_flow_endpoint():
    """Predict passenger flow risk"""
    if not flow_model:
        return jsonify({"error": "Passenger flow model not loaded"}), 503
    
    try:
        data = request.json
        result = predict_passenger_flow(flow_model, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/security', methods=['POST'])
def predict_security_endpoint():
    """Predict security congestion"""
    if not security_model:
        return jsonify({"error": "Security model not loaded"}), 503
    
    try:
        data = request.json
        events = data.get('events', [])
        result = predict_security_congestion(security_model, events)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/staff', methods=['POST'])
def predict_staff_endpoint():
    """Predict staffing risk"""
    if not staff_model:
        return jsonify({"error": "Staff model not loaded"}), 503
    
    try:
        data = request.json
        events = data.get('events', [])
        result = predict_staffing_risk(staff_model, events)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/predict/retail', methods=['POST'])
def predict_retail_endpoint():
    """Predict retail dwell risk"""
    if not retail_model:
        return jsonify({"error": "Retail model not loaded"}), 503
    
    try:
        data = request.json
        events = data.get('events', [])
        result = predict_retail_dwell_risk(retail_model, events)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/get_recommendation/<flight_id>', methods=['GET'])
def get_recommendation(flight_id):
    """Get AI recommendations for a specific flight"""
    flights = data_loader.get_current_flights(limit=15)
    flight = next((f for f in flights if f["id"] == flight_id), None)
    
    if flight:
        # Calculate risk using the new model
        flight['risk'] = get_ai_risk_score(flight)
        recommendation = generate_ai_recommendation(flight)
        return jsonify({
            "flight_id": flight_id, 
            "recommendation": recommendation,
            "risk": flight["risk"],
            "flight_data": flight
        })
    return jsonify({"error": "Flight not found"}), 404

@app.route('/api/apply_recommendation/<flight_id>', methods=['POST'])
def apply_recommendation(flight_id):
    """Apply AI recommendation and simulate risk reduction"""
    return jsonify({
        "success": True,
        "message": f"Recommendation applied for {flight_id}",
        "risk_reduction": 40,
        "delay_prevented": 28
    })

@app.route('/api/predict/events', methods=['POST'])
def predict_events():
    """Predict upcoming events based on current state"""
    try:
        data = request.json or {}
        time_horizon = int(data.get('time_horizon', 0))
        flights = data_loader.get_current_flights(limit=10)
        return jsonify(build_live_events(time_horizon, flights))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ============================================================================
# SOCKET.IO REAL-TIME SIMULATION
# ============================================================================

def simulation_loop():
    """Background task for real-time simulation updates"""
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
    print('✓ Client connected')
    socketio.start_background_task(simulation_loop)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🛫 AIRFLOW TWIN - AI Airport Operations Digital Twin")
    print("="*60)
    print("Starting server on http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5000)