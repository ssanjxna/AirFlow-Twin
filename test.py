from gemini_orchestrator import get_gemini_recommendation
from backend.airport_state_builder import build_airport_state
import json
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

from google import genai

client = genai.Client(
    api_key=GEMINI_API_KEY
)

airport_state = {
  "flight_id": "SQ-803",
  "specialist_outputs": {
    "delay": {"risk_probability": 0.87, "risk_percent": 87, "risk_level": "Critical"},
    "maintenance": {"risk_probability": 0.62, "risk_percent": 62, "risk_level": "High"},
    "passenger_flow": {"risk_probability": 0.73, "risk_percent": 73, "risk_level": "High"},
    "baggage": {"risk_probability": 0.54, "risk_percent": 54, "risk_level": "High"},
    "gate_events": {"risk_probability": 0.91, "risk_percent": 91, "risk_level": "Critical"},
    "security": {"risk_probability": 0.68, "risk_percent": 68, "risk_level": "High"},
    "staffing": {"risk_probability": 0.64, "risk_percent": 64, "risk_level": "High"},
    "retail": {"risk_probability": 0.44, "risk_percent": 44, "risk_level": "Medium"}
  },
  "overall_risk": {"risk_probability": 0.7424, "risk_percent": 74.24, "risk_level": "High"},
  "top_risk_sources": [
    {"source": "gate_events", "risk_percent": 91, "risk_level": "Critical"},
    {"source": "delay", "risk_percent": 87, "risk_level": "Critical"},
    {"source": "passenger_flow", "risk_percent": 73, "risk_level": "High"}
  ]
}

recommendation = get_gemini_recommendation(airport_state)

print("\nGEMINI RECOMMENDATION")
print(json.dumps(recommendation, indent=2))