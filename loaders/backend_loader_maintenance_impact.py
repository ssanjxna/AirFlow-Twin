
import pickle
import pandas as pd


def load_artifact(pkl_path):
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def predict_maintenance_impact(artifact, input_data):
    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in input_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    df = pd.DataFrame([input_data])[feature_columns]

    probability = float(
        pipeline.predict_proba(df)[0][list(pipeline.classes_).index(1)]
    )

    prediction = int(pipeline.predict(df)[0])

    if probability >= 0.85:
        risk_level = "critical"
    elif probability >= 0.65:
        risk_level = "high"
    elif probability >= 0.35:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "prediction": "Delay Risk" if prediction == 1 else "Low Delay Risk",
        "maintenance_delay_probability": probability,
        "maintenance_delay_percent": round(probability * 100, 2),
        "risk_level": risk_level,
        "model_version": artifact["model_version"],
        "note": "Maintenance-linked flight delay risk prediction."
    }
