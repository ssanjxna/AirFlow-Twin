
import pickle
import pandas as pd
import numpy as np


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


def parse_bool_series(series):
    return (
        series
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": 1, "false": 0, "1": 1, "0": 0})
        .fillna(0)
        .astype(int)
    )


def predict_retail_dwell_risk(artifact, retail_events):
    df = pd.DataFrame(retail_events)

    required = [
        "transaction_id",
        "staff_id",
        "flight_id",
        "transaction_time",
        "quantity",
        "unit_price",
        "total_price",
        "near_gate"
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required fields for retail engine: {missing}")

    df["transaction_time"] = pd.to_datetime(df["transaction_time"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
    df["near_gate"] = parse_bool_series(df["near_gate"])

    df = df.dropna(
        subset=[
            "transaction_id",
            "flight_id",
            "transaction_time",
            "quantity",
            "unit_price",
            "total_price"
        ]
    ).copy()

    if df.empty:
        return {
            "risk_probability": 0.0,
            "risk_percent": 0.0,
            "risk_level": "Low"
        }

    df["hour"] = df["transaction_time"].dt.hour
    df["is_peak_hour"] = df["hour"].isin(
        [6, 7, 8, 9, 17, 18, 19, 20]
    ).astype(int)

    df["transaction_hour_block"] = df["transaction_time"].dt.floor("H")

    df["transactions_same_hour"] = (
        df.groupby("transaction_hour_block")["transaction_id"]
        .transform("count")
    )

    df["revenue_same_hour"] = (
        df.groupby("transaction_hour_block")["total_price"]
        .transform("sum")
    )

    df["transactions_same_flight"] = (
        df.groupby("flight_id")["transaction_id"]
        .transform("count")
    )

    df["revenue_same_flight"] = (
        df.groupby("flight_id")["total_price"]
        .transform("sum")
    )

    df["near_gate_transactions_same_hour"] = (
        df.groupby("transaction_hour_block")["near_gate"]
        .transform("sum")
    )

    df["avg_spend_same_hour"] = (
        df.groupby("transaction_hour_block")["total_price"]
        .transform("mean")
    )

    score = (
        (df["transactions_same_hour"].rank(pct=True) * 100) * 0.25 +
        (df["revenue_same_hour"].rank(pct=True) * 100) * 0.20 +
        (df["transactions_same_flight"].rank(pct=True) * 100) * 0.15 +
        (df["revenue_same_flight"].rank(pct=True) * 100) * 0.10 +
        (df["near_gate_transactions_same_hour"].rank(pct=True) * 100) * 0.15 +
        (df["avg_spend_same_hour"].rank(pct=True) * 100) * 0.05 +
        (df["is_peak_hour"] * 100) * 0.10
    )

    risk_percent = float(np.clip(score.mean(), 0, 100))
    risk_percent = round(risk_percent, 2)
    risk_probability = round(risk_percent / 100, 4)

    return {
        "risk_probability": risk_probability,
        "risk_percent": risk_percent,
        "risk_level": risk_level_from_percent(risk_percent)
    }