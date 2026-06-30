
import pickle
import numpy as np
import pandas as pd


def load_artifact(pkl_path):
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def risk_level_from_percent(percent):
    percent = float(percent)

    if percent >= 75:
        return "Critical"
    elif percent >= 50:
        return "High"
    elif percent >= 25:
        return "Medium"
    return "Low"


def predict_baggage_risk(artifact, input_data):
    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in input_data]

    if missing:
        raise ValueError(f"Missing required fields for baggage model: {missing}")

    df = pd.DataFrame([input_data])[feature_columns]

    risk_percent = float(np.clip(pipeline.predict(df)[0], 0, 100))
    probability = risk_percent / 100

    return {
        "risk_probability": round(probability, 4),
        "risk_percent": round(risk_percent, 2),
        "risk_level": risk_level_from_percent(risk_percent)
    }
