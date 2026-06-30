import numpy as np
import joblib

from loaders.artifact_pipeline_utils import build_input_frame, predict


def load_artifact(pkl_path):
    return joblib.load(pkl_path)


def risk_label(score):
    score = float(score)

    if score >= 75:
        return "Critical"
    elif score >= 50:
        return "High"
    elif score >= 25:
        return "Medium"
    return "Low"


def predict_passenger_flow(artifact, input_data):
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in input_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    df = build_input_frame(feature_columns, input_data)

    score = float(np.clip(predict(artifact, df)[0], 0, 100))
    label = risk_label(score)

    return {
        "passenger_flow_risk_score": round(score, 2),
        "passenger_flow_risk_label": label,
        "risk_probability": round(score / 100, 4),
        "risk_percent": round(score, 2),
        "risk_level": label,
        "model_version": artifact["model_version"],
        "note": "Passenger flow risk score for airport operations reasoning."
    }
