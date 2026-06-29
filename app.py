import os
import time
import random
import joblib
import pandas as pd
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use the new Gemini API
try:
    from google import genai
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        client = genai.Client(api_key=gemini_api_key)
        GEMINI_AVAILABLE = True
        print("Gemini API configured successfully.")
    else:
        GEMINI_AVAILABLE = False
        print("WARNING: GEMINI_API_KEY not found in .env file")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"Gemini API not available: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize data loader
from utils.data_loader import AirportDataLoader
data_loader = AirportDataLoader('data')
data_loader.load_all_datasets()

# Load the trained AI model
try:
    ai_model = joblib.load('models/delay_predictor.pkl')
    label_encoders = joblib.load('models/label_encoders.pkl')
    print("AI model loaded successfully.")
except Exception as e:
    print(f"Could not load AI model: {e}")
    ai_model = None

# Global state
airport_state = {
    "current_time": "09:00",
    "flights": [],
    "resources": {}
}

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
        return """
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>Reassign maintenance crew to this flight</span>
        </div>
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>Open overflow parking for passenger traffic</span>
        </div>
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>Activate dynamic traffic signage</span>
        </div>
        """
    
    try:
        prompt = f"""
        Flight {flight['id']} from {flight['origin']} to {flight['destination']} 
        has a {flight['risk']}% delay risk with {flight.get('delay_minutes', 0)} minutes delay.
        Aircraft type: {flight.get('aircraft_type', 'A320')}, Gate: {flight['gate']}, 
        Status: {flight['status']}, Scheduled departure: {flight.get('scheduled_departure', 'N/A')}.
        
        Provide 3-4 specific operational recommendations to prevent delay.
        Format each recommendation as an HTML div with this exact structure:
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>RECOMMENDATION TEXT HERE</span>
        </div>
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return """
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>Reassign maintenance crew to this flight</span>
        </div>
        <div class="flex items-start gap-2 text-sm text-slate-300 mb-2">
            <svg class="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <span>Open overflow parking for passenger traffic</span>
        </div>
        """

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/flights')
def get_flights():
    flights = data_loader.get_current_flights(limit=15)
    resources = data_loader.get_resource_status()
    
    # Update risk scores with AI
    for flight in flights:
        flight['risk'] = get_ai_risk_score(flight)
    
    return jsonify({"flights": flights, "resources": resources})

@app.route('/api/simulate_future', methods=['POST'])
def simulate_future():
    data = request.json
    minutes_ahead = data.get('minutes', 0)
    
    flights = data_loader.get_current_flights(limit=15)
    
    future_flights = []
    total_delay_before = 0
    total_delay_after = 0
    
    # Simulate future risks (risks increase over time)
    for flight in flights:
        future_flight = flight.copy()
        base_risk = get_ai_risk_score(future_flight)
        # Risk increases by 5% every 10 minutes
        future_risk = min(100, base_risk + (minutes_ahead // 10) * 5)
        future_flight["risk"] = future_risk
        
        current_delay = future_flight.get('delay_minutes', 0) or 0
        future_delay = current_delay + (minutes_ahead // 10) * 2
        future_flight["delay_minutes"] = future_delay
        
        total_delay_before += current_delay
        total_delay_after += future_delay
        future_flights.append(future_flight)
    
    # Calculate AI impact
    delay_reduction = max(0, int(total_delay_after * 0.4))
    
    # --- PREDICTIVE EVENTS LOGIC ---
    predicted_event = None
    if minutes_ahead == 30:
        predicted_event = {
            "type": "warning",
            "title": "Maintenance Shift Change in 30m",
            "description": "Crew 2 is scheduled to leave. Flight SG-1280 requires ongoing maintenance.",
            "solution": "AI recommends delaying Crew 2 departure by 45m and reassigning Crew 3 to Gate A12."
        }
    elif minutes_ahead == 60:
        predicted_event = {
            "type": "info",
            "title": "Incoming Flight AF-882",
            "description": "Flight from Paris arriving in 60m. Gate B4 is currently blocked by baggage cart.",
            "solution": "AI dispatches Baggage Team Alpha to clear Gate B4 immediately."
        }

    return jsonify({
        "current_time": f"09:{minutes_ahead:02d}",
        "flights": future_flights,
        "resources": data_loader.get_resource_status(),
        "metrics": {
            "total_delay_before": total_delay_before,
            "total_delay_after": max(0, total_delay_after - delay_reduction),
            "delay_prevented": delay_reduction,
            "flights_delayed_before": len([f for f in future_flights if f['risk'] > 60]),
            "flights_delayed_after": max(0, len([f for f in future_flights if f['risk'] > 60]) - 2)
        },
        "predicted_event": predicted_event
    })

@app.route('/api/get_recommendation/<flight_id>', methods=['GET'])
def get_recommendation(flight_id):
    flights = data_loader.get_current_flights(limit=15)
    flight = next((f for f in flights if f["id"] == flight_id), None)
    
    if flight:
        recommendation = generate_ai_recommendation(flight)
        return jsonify({
            "flight_id": flight_id, 
            "recommendation": recommendation,
            "risk": flight["risk"],
            "flight_data": flight
        })
    return jsonify({"error": "Flight not found"}), 404

@app.route('/api/resource_status')
def get_resource_status():
    return jsonify(data_loader.get_resource_status())

@app.route('/api/apply_recommendation/<flight_id>', methods=['POST'])
def apply_recommendation(flight_id):
    return jsonify({
        "success": True,
        "message": f"Recommendation applied for {flight_id}",
        "risk_reduction": 40,
        "delay_prevented": 28
    })

def simulation_loop():
    while True:
        flights = data_loader.get_current_flights(limit=15)
        
        for flight in flights:
            base_risk = get_ai_risk_score(flight)
            fluctuation = random.randint(-3, 3)
            flight["risk"] = max(0, min(100, base_risk + fluctuation))
        
        airport_state["flights"] = flights
        airport_state["resources"] = data_loader.get_resource_status()
        
        socketio.emit('update_map', airport_state)
        socketio.sleep(3)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.start_background_task(simulation_loop)

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)