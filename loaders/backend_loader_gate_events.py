
import pickle
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


def calculate_overlap_minutes(start1, end1, start2, end2):
    latest_start = max(start1, start2)
    earliest_end = min(end1, end2)
    overlap = (earliest_end - latest_start).total_seconds() / 60
    return max(0, int(overlap))


def calculate_gate_risk_probability(conflicts, delay_risks, load_risks):
    score = 0

    score += min(len(conflicts) * 25, 60)
    score += min(len(delay_risks) * 15, 30)
    score += min(len(load_risks) * 10, 20)

    score = min(score, 100)

    return score / 100, score


def detect_gate_event_risks(artifact, events):
    df = pd.DataFrame(events)

    for col in ["event_time", "scheduled_gate_time", "actual_gate_time", "created_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["passenger_count"] = pd.to_numeric(
        df.get("passenger_count", 0),
        errors="coerce"
    ).fillna(0)

    df = df.dropna(subset=["flight_id", "gate", "event_time"]).copy()

    df["event_hour"] = df["event_time"].dt.hour

    df["gate_delay_minutes"] = (
        df["actual_gate_time"] - df["scheduled_gate_time"]
    ).dt.total_seconds() / 60

    df["gate_delay_minutes"] = df["gate_delay_minutes"].fillna(0).abs()

    df["time_window_start"] = df["event_time"]

    df["time_window_end"] = df["event_time"] + pd.to_timedelta(
        df["passenger_count"].clip(lower=30, upper=250) / 4,
        unit="m"
    )

    conflicts = []

    for gate, group in df.sort_values(["gate", "time_window_start"]).groupby("gate"):
        group = group.sort_values("time_window_start").reset_index(drop=True)

        for i in range(len(group)):
            current = group.iloc[i]

            for j in range(i + 1, len(group)):
                next_event = group.iloc[j]

                if next_event["time_window_start"] > current["time_window_end"]:
                    break

                overlap_minutes = calculate_overlap_minutes(
                    current["time_window_start"],
                    current["time_window_end"],
                    next_event["time_window_start"],
                    next_event["time_window_end"]
                )

                if overlap_minutes > 0:
                    conflicts.append({
                        "gate": gate,
                        "flight_1": current["flight_id"],
                        "flight_2": next_event["flight_id"],
                        "overlap_minutes": overlap_minutes
                    })

    delay_risks = []

    delayed = df[df["gate_delay_minutes"] > 10]

    for _, row in delayed.iterrows():
        delay_risks.append({
            "gate": row["gate"],
            "flight_id": row["flight_id"],
            "gate_delay_minutes": round(float(row["gate_delay_minutes"]), 2)
        })

    load_risks = []

    gate_hour_load = (
        df.groupby(["gate", "event_hour"])
        .agg(
            events=("flight_id", "count"),
            passengers=("passenger_count", "sum")
        )
        .reset_index()
    )

    high_load = gate_hour_load[
        (gate_hour_load["events"] >= 3) |
        (gate_hour_load["passengers"] >= 300)
    ]

    for _, row in high_load.iterrows():
        load_risks.append({
            "gate": row["gate"],
            "hour": int(row["event_hour"]),
            "events": int(row["events"]),
            "passengers": int(row["passengers"])
        })

    risk_probability, risk_percent = calculate_gate_risk_probability(
        conflicts,
        delay_risks,
        load_risks
    )

    risk_percent = round(risk_percent, 2)

    return {
        "risk_probability": round(risk_probability, 4),
        "risk_percent": risk_percent,
        "risk_level": risk_level_from_percent(risk_percent)
    }
