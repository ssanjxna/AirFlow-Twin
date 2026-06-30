
import pickle
import pandas as pd


def load_artifact(pkl_path):
    with open(pkl_path, "rb") as f:
        artifact = pickle.load(f)
    return artifact


def predict_congestion(artifact, airport_data):
    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]
    label_map = artifact["config"]["label_map"]

    missing = [col for col in feature_columns if col not in airport_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    input_df = pd.DataFrame([airport_data])[feature_columns]

    prediction = int(pipeline.predict(input_df)[0])
    probabilities = pipeline.predict_proba(input_df)[0]

    return {
        "congestion_level": label_map[prediction],
        "congestion_class": prediction,
        "probabilities": {
            "Low": round(float(probabilities[0]) * 100, 2),
            "Medium": round(float(probabilities[1]) * 100, 2),
            "High": round(float(probabilities[2]) * 100, 2)
        },
        "model_version": artifact["model_version"],
        "note": "Airport congestion prediction only."
    }
