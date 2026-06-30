import time
import requests
from datetime import datetime, timedelta

API_URL = "http://127.0.0.1:5000/api/simulator/add-flight"
# If your app runs on port 8000, change to:
# API_URL = "http://127.0.0.1:8000/api/simulator/add-flight"


def make_flight(index, risk_scenario):
    now = datetime.now()

    return {
        "flight_id": f"SIM{index:03}",
        "airline": "Air Mauritius",
        "flight_number": f"MK{100 + index}",
        "origin": "Rodrigues" if index == 1 else "Dubai",
        "destination": "Mauritius",
        "scheduled_arrival": (now + timedelta(minutes=index * 5)).strftime("%Y-%m-%d %H:%M:%S"),
        "scheduled_departure": (now + timedelta(minutes=45 + index * 10)).strftime("%Y-%m-%d %H:%M:%S"),
        "aircraft_type": "ATR72" if index == 1 else "A350",
        "status": "scheduled",

        # demo risk drivers
        "scenario": risk_scenario,
        "maintenance_required": risk_scenario == "HIGH",
        "fuel_required": True,
        "baggage_load": "LOW" if risk_scenario == "LOW" else "HIGH",
        "security_queue_level": "NORMAL" if risk_scenario == "LOW" else "CONGESTED",
        "gate_conflict": risk_scenario == "MEDIUM"
    }


def run_demo():
    flights = [
        make_flight(1, "LOW"),
        make_flight(2, "MEDIUM"),
        make_flight(3, "HIGH"),
    ]

    print("Starting AirFlow Twin live simulator...")

    for flight in flights:
        print(f"\nInserting {flight['flight_id']} - {flight['scenario']} risk")

        try:
            response = requests.post(API_URL, json=flight, timeout=10)
            print("Status:", response.status_code)
            print("Response:", response.json())
        except Exception as e:
            print("Failed to send flight:", e)

        time.sleep(10)

    print("\nLive simulation completed.")


if __name__ == "__main__":
    run_demo()