import pandas as pd


def get_pipeline_parts(artifact):
    pipeline = artifact["pipeline"]
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    if hasattr(model, "n_jobs"):
        try:
            model.set_params(n_jobs=1)
        except Exception:
            try:
                model.n_jobs = 1
            except Exception:
                pass

    return preprocessor, model


def build_input_frame(feature_columns, input_data):
    return pd.DataFrame([input_data])[feature_columns]


def transform_input(artifact, input_df):
    preprocessor, model = get_pipeline_parts(artifact)
    transformed = preprocessor.transform(input_df)
    return model, transformed


def predict(artifact, input_df):
    model, transformed = transform_input(artifact, input_df)
    return model.predict(transformed)


def predict_proba(artifact, input_df):
    model, transformed = transform_input(artifact, input_df)
    return model.predict_proba(transformed)
