import joblib

from loaders.artifact_pipeline_utils import build_input_frame, predict, predict_proba


def load_artifact(pkl_path):
    return joblib.load(pkl_path)


def predict_congestion(artifact, airport_data):
    feature_columns = artifact["feature_columns"]
    label_map = artifact["config"]["label_map"]

    missing = [col for col in feature_columns if col not in airport_data]

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    input_df = build_input_frame(feature_columns, airport_data)

    prediction = int(predict(artifact, input_df)[0])
    probabilities = predict_proba(artifact, input_df)[0]

    return {
        "congestion_level": label_map.get(prediction, label_map.get(str(prediction), "Unknown")),
        "congestion_class": prediction,
        "probabilities": {
            "Low": round(float(probabilities[0]) * 100, 2),
            "Medium": round(float(probabilities[1]) * 100, 2),
            "High": round(float(probabilities[2]) * 100, 2)
        },
        "model_version": artifact["model_version"],
        "note": "Airport congestion prediction only."
    }
