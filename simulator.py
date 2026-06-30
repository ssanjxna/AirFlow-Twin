import os
import time
from datetime import datetime, timedelta

import requests

API_URL = os.getenv(
    "AIRFLOW_TWIN_API_URL",
    "http://127.0.0.1:5000/api/simulator/add-flight"
)


def make_flight(
    flight_id,
    flight_number,
    airline,
    origin,
    aircraft_type,
    risk_scenario,
    arrival_min,
    departure_min,
    critical=False
):
    now = datetime.now()

    is_high_pressure = risk_scenario in ["HIGH", "CRITICAL"] or critical

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

        # AI risk drivers
        # Keep scenario as HIGH for critical because many backends only handle LOW/MEDIUM/HIGH.
        "scenario": "HIGH" if critical else risk_scenario,
        "maintenance_required": is_high_pressure,
        "fuel_required": True,
        "baggage_load": "HIGH" if is_high_pressure else "LOW",
        "security_queue_level": "CONGESTED" if is_high_pressure else "NORMAL",
        "gate_conflict": risk_scenario in ["MEDIUM", "HIGH", "CRITICAL"] or critical,
    }


def run_demo(interval_seconds=10):
    # Unique run tag so flight_id and flight_number do not collide with old database records
    run_tag = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = run_tag[-6:]

    flights = [
        {
            "label": "LOW",
            "data": make_flight(
                flight_id=f"SIM{suffix}11",
                flight_number=f"MK{suffix}1",
                airline="Air Mauritius",
                origin="Reunion",
                aircraft_type="ATR72",
                risk_scenario="LOW",
                arrival_min=8,
                departure_min=90,
            ),
        },
        {
            "label": "MEDIUM",
            "data": make_flight(
                flight_id=f"SIM{suffix}12",
                flight_number=f"UU{suffix}2",
                airline="Air Austral",
                origin="Saint-Denis",
                aircraft_type="B737",
                risk_scenario="MEDIUM",
                arrival_min=16,
                departure_min=62,
            ),
        },
        {
            "label": "HIGH",
            "data": make_flight(
                flight_id=f"SIM{suffix}13",
                flight_number=f"AF{suffix}3",
                airline="Air France",
                origin="Paris",
                aircraft_type="B777",
                risk_scenario="HIGH",
                arrival_min=24,
                departure_min=48,
            ),
        },
        {
            "label": "CRITICAL",
            "data": make_flight(
                flight_id=f"SIM{suffix}14",
                flight_number=f"SV{suffix}4",
                airline="Saudia",
                origin="Jeddah",
                aircraft_type="B787",
                risk_scenario="HIGH",
                arrival_min=30,
                departure_min=38,
                critical=True,
            ),
        },
    ]

    print(f"Starting AirFlow Twin live simulator -> {API_URL}")
    print(f"Demo run tag: {run_tag}")

    for item in flights:
        flight = item["data"]
        label = item["label"]

        print(f"\nInserting {flight['flight_id']} - {label} risk")
        print(f"Flight: {flight['flight_number']} | {flight['airline']} from {flight['origin']}")
        print(f"Arrival: {flight['scheduled_arrival']}")
        print(f"Departure: {flight['scheduled_departure']}")

        try:
            response = requests.post(API_URL, json=flight, timeout=10)
            print("Status:", response.status_code)

            try:
                print("Response:", response.json())
            except Exception:
                print("Response text:", response.text)

        except Exception as exc:
            print("Failed to send flight:", exc)

        if item != flights[-1]:
            time.sleep(interval_seconds)

    print("\nLive simulation completed.")


if __name__ == "__main__":
    run_demo()