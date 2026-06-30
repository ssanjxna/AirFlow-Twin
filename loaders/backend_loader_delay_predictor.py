
import pickle
import pandas as pd


def load_artifact(pkl_path):
    with open(pkl_path, "rb") as f:
        artifact = pickle.load(f)
    return artifact


def map_delay_probability(probability):
    probability = float(probability)

    if probability >= 0.85:
        return {
            "risk_level": "critical",
            "priority": "immediate_action"
        }

    if probability >= 0.65:
        return {
            "risk_level": "high",
            "priority": "urgent_monitoring"
        }

    if probability >= 0.35:
        return {
            "risk_level": "medium",
            "priority": "watch"
        }

    return {
        "risk_level": "low",
        "priority": "normal"
    }


def predict_delay(artifact, flight_data):
    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in flight_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    input_df = pd.DataFrame([flight_data])[feature_columns]

    probability = float(pipeline.predict_proba(input_df)[0, 1])
    prediction = int(pipeline.predict(input_df)[0])

    risk = map_delay_probability(probability)

    return {
        "prediction": "Delayed" if prediction == 1 else "On-Time",
        "delay_probability": probability,
        "delay_risk_percent": round(probability * 100, 2),
        "risk_level": risk["risk_level"],
        "priority": risk["priority"],
        "model_version": artifact["model_version"],
        "note": "Operational flight-delay prediction only."
    }