
import pickle
import numpy as np
import pandas as pd


def load_artifact(pkl_path):
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


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
    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in input_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    df = pd.DataFrame([input_data])[feature_columns]

    score = float(np.clip(pipeline.predict(df)[0], 0, 100))
    label = risk_label(score)

    return {
        "passenger_flow_risk_score": round(score, 2),
        "passenger_flow_risk_label": label,
        "risk_level": label,
        "model_version": artifact["model_version"],
        "note": "Passenger flow risk score for airport operations reasoning."
    }
