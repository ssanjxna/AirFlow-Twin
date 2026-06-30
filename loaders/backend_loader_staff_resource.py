
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


def predict_staffing_risk(artifact, staff_events):
    df = pd.DataFrame(staff_events)

    required = [
        "staff_id",
        "shift_date",
        "shift_start",
        "shift_end",
        "assigned_gate",
        "scheduled_hours",
        "is_absent",
        "last_training_date"
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required fields for staffing engine: {missing}")

    df["shift_date"] = pd.to_datetime(df["shift_date"], errors="coerce")
    df["shift_start"] = pd.to_datetime(df["shift_start"], errors="coerce")
    df["shift_end"] = pd.to_datetime(df["shift_end"], errors="coerce")
    df["last_training_date"] = pd.to_datetime(df["last_training_date"], errors="coerce")

    df["scheduled_hours"] = pd.to_numeric(df["scheduled_hours"], errors="coerce")
    df["is_absent"] = parse_bool_series(df["is_absent"])

    df = df.dropna(
        subset=[
            "staff_id",
            "shift_date",
            "shift_start",
            "shift_end",
            "scheduled_hours"
        ]
    ).copy()

    if df.empty:
        return {
            "risk_probability": 0.0,
            "risk_percent": 0.0,
            "risk_level": "Low"
        }

    df["shift_start_hour"] = df["shift_start"].dt.hour
    df["is_peak_shift"] = df["shift_start_hour"].isin(
        [6, 7, 8, 9, 17, 18, 19, 20]
    ).astype(int)

    df["actual_shift_hours"] = (
        df["shift_end"] - df["shift_start"]
    ).dt.total_seconds().abs() / 3600

    df["training_age_days"] = (
        df["shift_date"] - df["last_training_date"]
    ).dt.days.abs()

    df["shift_hour_block"] = df["shift_start"].dt.floor("H")

    df["staff_same_hour"] = (
        df.groupby("shift_hour_block")["staff_id"]
        .transform("count")
    )

    df["staff_same_gate_hour"] = (
        df.groupby(["assigned_gate", "shift_hour_block"])["staff_id"]
        .transform("count")
    )

    df["absent_same_hour"] = (
        df.groupby("shift_hour_block")["is_absent"]
        .transform("sum")
    )

    df["avg_training_age_same_hour"] = (
        df.groupby("shift_hour_block")["training_age_days"]
        .transform("mean")
    )

    df["avg_shift_hours_same_hour"] = (
        df.groupby("shift_hour_block")["actual_shift_hours"]
        .transform("mean")
    )

    coverage_score = (1 - df["staff_same_hour"].rank(pct=True)) * 100
    gate_coverage_score = (1 - df["staff_same_gate_hour"].rank(pct=True)) * 100
    absence_score = df["absent_same_hour"].rank(pct=True) * 100
    training_age_score = df["avg_training_age_same_hour"].rank(pct=True) * 100
    long_shift_score = df["avg_shift_hours_same_hour"].rank(pct=True) * 100
    peak_score = df["is_peak_shift"] * 100

    score = (
        coverage_score * 0.30 +
        gate_coverage_score * 0.25 +
        absence_score * 0.15 +
        training_age_score * 0.10 +
        long_shift_score * 0.10 +
        peak_score * 0.10
    )

    risk_percent = float(np.clip(score.mean(), 0, 100))
    risk_percent = round(risk_percent, 2)
    risk_probability = round(risk_percent / 100, 4)

    return {
        "risk_probability": risk_probability,
        "risk_percent": risk_percent,
        "risk_level": risk_level_from_percent(risk_percent)
    }
