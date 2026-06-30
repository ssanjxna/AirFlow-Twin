import os
import time
import random
import joblib
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

# Initialize data loader
from utils.data_loader import AirportDataLoader
data_loader = AirportDataLoader('data')
data_loader.load_all_datasets()
print("✓ Airport data loaded successfully.")

# Load the trained AI delay prediction model
try:
    ai_model = joblib.load('models/delay_predictor.pkl')
    label_encoders = joblib.load('models/label_encoders.pkl')
    print("✓ AI delay predictor model loaded successfully.")
except Exception as e:
    print(f"⚠ Could not load AI model: {e}")
    ai_model = None
    label_encoders = None

# Initialize parking congestion predictor
from models.parking_predictor import ParkingCongestionPredictor
parking_predictor = ParkingCongestionPredictor()

try:
    parking_predictor.load_model()
    print("✓ Parking congestion predictor loaded successfully.")
except Exception as e:
    print(f"⚠ Training new parking predictor: {e}")
    parking_predictor.train()

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
    if ai_model is None:
        return flight.get('risk', 50)
    try:
        data = {
            'origin': [flight.get('origin', 'DEL')],
            'destination': [flight.get('destination', 'SIN')],
            'airline_code': [flight.get('airline_code', 'UK')],
            'distance': [flight.get('distance', 1000)],
            'time_of_day': [flight.get('time_of_day', 'Morning')],
            'day_of_week': [flight.get('day_of_week', 'Mon')]
        }
        df = pd.DataFrame(data)
        for col in ['origin', 'destination', 'airline_code', 'time_of_day', 'day_of_week']:
            if col in label_encoders:
                try:
                    df[col] = label_encoders[col].transform(df[col].astype(str))
                except ValueError:
                    df[col] = 0 
        prob = ai_model.predict_proba(df)[0][1]
        return int(prob * 100)
    except Exception as e:
        print(f"AI prediction error: {e}")
        return flight.get('risk', 50)

def generate_ai_recommendation(flight):
    if not GEMINI_AVAILABLE:
        return "<div class='text-slate-400'>AI Recommendations unavailable (API Key missing).</div>"
    try:
        prompt = f"Flight {flight['id']} has a {flight['risk']}% delay risk. Give 3 short operational recommendations as bullet points."
        response = client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt)
        return response.text
    except Exception as e:
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
    flights = data_loader.get_current_flights(limit=15)
    resources = data_loader.get_resource_status()
    
    # Update risk scores with AI model
    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)
    
    return jsonify({"flights": flights, "resources": resources})

@app.route('/api/parking_status')
def get_parking_status():
    """Get current parking congestion status and predictions"""
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