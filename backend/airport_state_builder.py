# ============================================================
# AIRFLOW TWIN - LAYER 2: AIRPORT STATE BUILDER
# Combines all specialist outputs into one Gemini-ready state
# ============================================================

import json
from datetime import datetime


# ------------------------------------------------------------
# 1. Risk utilities
# ------------------------------------------------------------

def risk_level_from_percent(percent):
    percent = float(percent)

    if percent >= 75:
        return "Critical"
    elif percent >= 50:
        return "High"
    elif percent >= 25:
        return "Medium"
    return "Low"


def normalize_specialist_output(output):
    """
    Ensures every specialist output has:
    - risk_probability
    - risk_percent
    - risk_level
    """

    if output is None:
        return {
            "risk_probability": 0.0,
            "risk_percent": 0.0,
            "risk_level": "Low"
        }

    risk_probability = float(output.get("risk_probability", 0.0))
    risk_percent = float(output.get("risk_percent", risk_probability * 100))

    risk_probability = max(0.0, min(risk_probability, 1.0))
    risk_percent = max(0.0, min(risk_percent, 100.0))

    return {
        "risk_probability": round(risk_probability, 4),
        "risk_percent": round(risk_percent, 2),
        "risk_level": output.get(
            "risk_level",
            risk_level_from_percent(risk_percent)
        )
    }


# ------------------------------------------------------------
# 2. Airport state builder
# ------------------------------------------------------------

def build_airport_state(
    flight_id,
    delay_output=None,
    maintenance_output=None,
    passenger_flow_output=None,
    baggage_output=None,
    gate_events_output=None,
    security_output=None,
    staffing_output=None,
    retail_output=None
):
    airport_state = {
        "flight_id": flight_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",

        "specialist_outputs": {
            "delay": normalize_specialist_output(delay_output),
            "maintenance": normalize_specialist_output(maintenance_output),
            "passenger_flow": normalize_specialist_output(passenger_flow_output),
            "baggage": normalize_specialist_output(baggage_output),
            "gate_events": normalize_specialist_output(gate_events_output),
            "security": normalize_specialist_output(security_output),
            "staffing": normalize_specialist_output(staffing_output),
            "retail": normalize_specialist_output(retail_output)
        }
    }

    airport_state["overall_risk"] = calculate_overall_airport_risk(
        airport_state["specialist_outputs"]
    )

    airport_state["top_risk_sources"] = get_top_risk_sources(
        airport_state["specialist_outputs"]
    )

    return airport_state


# ------------------------------------------------------------
# 3. Overall risk calculation
# ------------------------------------------------------------

def calculate_overall_airport_risk(specialist_outputs):
    """
    Weighted airport risk score.
    Delay, gate, passenger flow, baggage, and staffing matter most.
    """

    weights = {
        "delay": 0.25,
        "gate_events": 0.18,
        "passenger_flow": 0.15,
        "baggage": 0.12,
        "maintenance": 0.12,
        "security": 0.08,
        "staffing": 0.07,
        "retail": 0.03
    }

    total_score = 0

    for model_name, weight in weights.items():
        total_score += (
            specialist_outputs[model_name]["risk_percent"] * weight
        )

    total_score = round(total_score, 2)

    return {
        "risk_probability": round(total_score / 100, 4),
        "risk_percent": total_score,
        "risk_level": risk_level_from_percent(total_score)
    }


# ------------------------------------------------------------
# 4. Top risk source extraction
# ------------------------------------------------------------

def get_top_risk_sources(specialist_outputs, top_n=3):
    ranked = sorted(
        specialist_outputs.items(),
        key=lambda item: item[1]["risk_percent"],
        reverse=True
    )

    return [
        {
            "source": name,
            "risk_percent": data["risk_percent"],
            "risk_level": data["risk_level"]
        }
        for name, data in ranked[:top_n]
    ]


# ------------------------------------------------------------
# 5. Example usage
# Replace these with real specialist outputs from your models
# ------------------------------------------------------------

delay_output = {
    "risk_probability": 0.87,
    "risk_percent": 87,
    "risk_level": "Critical"
}

maintenance_output = {
    "risk_probability": 0.62,
    "risk_percent": 62,
    "risk_level": "High"
}

passenger_flow_output = {
    "risk_probability": 0.73,
    "risk_percent": 73,
    "risk_level": "High"
}

baggage_output = {
    "risk_probability": 0.54,
    "risk_percent": 54,
    "risk_level": "High"
}

gate_events_output = {
    "risk_probability": 0.91,
    "risk_percent": 91,
    "risk_level": "Critical"
}

security_output = {
    "risk_probability": 0.68,
    "risk_percent": 68,
    "risk_level": "High"
}

staffing_output = {
    "risk_probability": 0.64,
    "risk_percent": 64,
    "risk_level": "High"
}

retail_output = {
    "risk_probability": 0.44,
    "risk_percent": 44,
    "risk_level": "Medium"
}


airport_state = build_airport_state(
    flight_id="SQ-803",
    delay_output=delay_output,
    maintenance_output=maintenance_output,
    passenger_flow_output=passenger_flow_output,
    baggage_output=baggage_output,
    gate_events_output=gate_events_output,
    security_output=security_output,
    staffing_output=staffing_output,
    retail_output=retail_output
)

print(json.dumps(airport_state, indent=2))