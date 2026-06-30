import joblib

from loaders.artifact_pipeline_utils import build_input_frame, predict, predict_proba


def load_artifact(pkl_path):
    return joblib.load(pkl_path)


def predict_maintenance_impact(artifact, input_data):
    feature_columns = artifact["feature_columns"]

    missing = [col for col in feature_columns if col not in input_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    df = build_input_frame(feature_columns, input_data)

    probability = float(
        predict_proba(artifact, df)[0][list(artifact["pipeline"].named_steps["model"].classes_).index(1)]
    )

    prediction = int(predict(artifact, df)[0])

    if probability >= 0.85:
        risk_level = "critical"
    elif probability >= 0.65:
        risk_level = "high"
    elif probability >= 0.35:
        risk_level = "medium"
    else:
        risk_level = "low"

    risk_percent = round(probability * 100, 2)

    return {
        "prediction": "Delay Risk" if prediction == 1 else "Low Delay Risk",
        "maintenance_delay_probability": probability,
        "maintenance_delay_percent": risk_percent,
        "risk_probability": round(probability, 4),
        "risk_percent": risk_percent,
        "risk_level": risk_level,
        "model_version": artifact["model_version"],
        "note": "Maintenance-linked flight delay risk prediction."
    }
