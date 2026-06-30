
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


def predict_security_congestion(artifact, security_events):
    df = pd.DataFrame(security_events)

    required = [
        "screening_id",
        "lane_number",
        "arrival_time",
        "screening_start_time",
        "screening_end_time",
        "planned_screening_seconds",
        "lane_capacity_per_hour",
        "staff_capacity_per_hour",
        "scanner_capacity_per_hour",
        "alarm_triggered",
        "manual_check_required",
        "secondary_screening"
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required fields for security engine: {missing}")

    for col in ["arrival_time", "screening_start_time", "screening_end_time"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in [
        "lane_number",
        "planned_screening_seconds",
        "lane_capacity_per_hour",
        "staff_capacity_per_hour",
        "scanner_capacity_per_hour"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        "alarm_triggered",
        "manual_check_required",
        "secondary_screening"
    ]:
        df[col] = parse_bool_series(df[col])

    df = df.dropna(
        subset=[
            "screening_id",
            "lane_number",
            "arrival_time",
            "screening_start_time",
            "screening_end_time",
            "planned_screening_seconds"
        ]
    ).copy()

    if df.empty:
        return {
            "risk_probability": 0.0,
            "risk_percent": 0.0,
            "risk_level": "Low"
        }

    df["arrival_hour"] = df["arrival_time"].dt.hour
    df["is_peak_hour"] = df["arrival_hour"].isin(
        [6, 7, 8, 9, 17, 18, 19, 20]
    ).astype(int)

    df["actual_screening_seconds"] = (
        df["screening_end_time"] - df["screening_start_time"]
    ).dt.total_seconds().abs()

    df["waiting_seconds"] = (
        df["screening_start_time"] - df["arrival_time"]
    ).dt.total_seconds().abs()

    df["screening_delay_ratio"] = (
        df["actual_screening_seconds"] / df["planned_screening_seconds"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    df["arrival_hour_block"] = df["arrival_time"].dt.floor("H")

    df["passengers_same_hour"] = (
        df.groupby("arrival_hour_block")["screening_id"]
        .transform("count")
    )

    df["passengers_same_lane_hour"] = (
        df.groupby(["lane_number", "arrival_hour_block"])["screening_id"]
        .transform("count")
    )

    df["alarms_same_hour"] = (
        df.groupby("arrival_hour_block")["alarm_triggered"]
        .transform("sum")
    )

    df["manual_checks_same_hour"] = (
        df.groupby("arrival_hour_block")["manual_check_required"]
        .transform("sum")
    )

    df["secondary_screenings_same_hour"] = (
        df.groupby("arrival_hour_block")["secondary_screening"]
        .transform("sum")
    )

    df["capacity_pressure"] = (
        df["passengers_same_hour"] / df["lane_capacity_per_hour"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    df["lane_pressure"] = (
        df["passengers_same_lane_hour"] / df["scanner_capacity_per_hour"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    score = (
        (df["passengers_same_hour"].rank(pct=True) * 100) * 0.20 +
        (df["passengers_same_lane_hour"].rank(pct=True) * 100) * 0.15 +
        (df["waiting_seconds"].rank(pct=True) * 100) * 0.15 +
        (df["screening_delay_ratio"].rank(pct=True) * 100) * 0.15 +
        (df["alarms_same_hour"].rank(pct=True) * 100) * 0.07 +
        (df["manual_checks_same_hour"].rank(pct=True) * 100) * 0.07 +
        (df["secondary_screenings_same_hour"].rank(pct=True) * 100) * 0.07 +
        (df["capacity_pressure"].rank(pct=True) * 100) * 0.07 +
        (df["lane_pressure"].rank(pct=True) * 100) * 0.04 +
        (df["is_peak_hour"] * 100) * 0.03
    )

    risk_percent = float(np.clip(score.mean(), 0, 100))
    risk_percent = round(risk_percent, 2)
    risk_probability = round(risk_percent / 100, 4)

    return {
        "risk_probability": risk_probability,
        "risk_percent": risk_percent,
        "risk_level": risk_level_from_percent(risk_percent)
    }
