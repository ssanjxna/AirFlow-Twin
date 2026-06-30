import joblib

from loaders.artifact_pipeline_utils import build_input_frame, predict, predict_proba


def load_artifact(pkl_path):
    return joblib.load(pkl_path)


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
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in flight_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    input_df = build_input_frame(feature_columns, flight_data)

    probability = float(predict_proba(artifact, input_df)[0, 1])
    prediction = int(predict(artifact, input_df)[0])

    risk = map_delay_probability(probability)
    risk_percent = round(probability * 100, 2)

    return {
        "prediction": "Delayed" if prediction == 1 else "On-Time",
        "delay_probability": probability,
        "delay_risk_percent": risk_percent,
        "risk_probability": round(probability, 4),
        "risk_percent": risk_percent,
        "risk_level": risk["risk_level"],
        "priority": risk["priority"],
        "model_version": artifact["model_version"],
        "note": "Operational flight-delay prediction only."
    }
