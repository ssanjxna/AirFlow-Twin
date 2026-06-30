import os
import time
from datetime import datetime, timedelta

import requests

API_URL = os.getenv("AIRFLOW_TWIN_API_URL", "http://127.0.0.1:5000/api/simulator/add-flight")


def make_flight(flight_id, flight_number, airline, origin, aircraft_type, risk_scenario, arrival_min, departure_min):
    now = datetime.now()
    return {
        "flight_id": flight_id,
        "flight_number": flight_number,
        "airline": airline,
        "origin": origin,
        "destination": "Mauritius",
        "scheduled_arrival": (now + timedelta(minutes=arrival_min)).strftime("%Y-%m-%d %H:%M:%S"),
        "scheduled_departure": (now + timedelta(minutes=departure_min)).strftime("%Y-%m-%d %H:%M:%S"),
        "aircraft_type": aircraft_type,
        "status": "scheduled",
        "scenario": risk_scenario,
        "maintenance_required": risk_scenario == "HIGH",
        "fuel_required": True,
        "baggage_load": "LOW" if risk_scenario == "LOW" else "HIGH",
        "security_queue_level": "NORMAL" if risk_scenario == "LOW" else "CONGESTED",
        "gate_conflict": risk_scenario in ["MEDIUM", "HIGH"],
    }


def run_demo(interval_seconds=10):
    flights = [
        make_flight("SIM301", "MK901", "Air Mauritius", "Rodrigues", "ATR72", "LOW", 5, 70),
        make_flight("SIM302", "BA442", "British Airways", "London", "B787", "MEDIUM", 15, 50),
        make_flight("SIM303", "AF671", "Air France", "Paris", "A350", "HIGH", 20, 35),
    ]

    print(f"Starting AirFlow Twin live simulator -> {API_URL}")

    for flight in flights:
        print(f"\nInserting {flight['flight_id']} - {flight['scenario']} risk")
        try:
            response = requests.post(API_URL, json=flight, timeout=10)
            print("Status:", response.status_code)
            try:
                print("Response:", response.json())
            except Exception:
                print("Response text:", response.text)
        except Exception as exc:
            print("Failed to send flight:", exc)

        if flight != flights[-1]:
            time.sleep(interval_seconds)

    print("\nLive simulation completed.")


if __name__ == "__main__":
    run_demo()
